package pde.review;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Review pipeline for the slice.
 *
 * Gates run before any model output, and model output must pass the same
 * gates before aggregation: scope (Java only), empty diff, format-only and
 * comment-only diffs, dedup, severity sort, secret redaction, and
 * autoMerge always false.
 *
 * The rule lanes below are deterministic checks for known patterns
 * (SQL concatenation, hard-coded secrets, missing null checks, empty
 * catch blocks, over-long lines). They are the offline stand-in for the
 * review lanes; in production, replace each lane's findings with Spring AI
 * ChatClient structured output using prompts/pr-review.md, keeping the
 * same gates, and keep the rule lanes as a pre-model static check.
 */
public class ReviewService {

    private static final Pattern SQL_CONCAT =
            Pattern.compile("\"(?:SELECT|INSERT|UPDATE|DELETE)[^\"]*\"\\s*\\+");
    private static final Pattern SECRET =
            Pattern.compile("(?i)(password|passwd|secret|api[_-]?key)\\s*=\\s*\"([^\"]+)\"");
    private static final Pattern EMPTY_CATCH =
            Pattern.compile("catch\\s*\\([^)]*\\)\\s*\\{\\s*\\}");
    private static final Pattern NULL_CALL =
            Pattern.compile("([A-Za-z_][A-Za-z0-9_]*)\\.(get[A-Za-z0-9_]*)\\(");

    private static int severityRank(String severity) {
        return switch (severity) {
            case "high" -> 0;
            case "medium" -> 1;
            default -> 2;
        };
    }

    public ReviewResult review(String diff) {
        if (diff == null || diff.isBlank()) {
            return new ReviewResult("", List.of(), true, "空 diff，无法评审。", false);
        }
        DiffChunker.ParsedDiff parsed = DiffChunker.parse(diff);
        if (!parsed.files().isEmpty()
                && parsed.files().stream().noneMatch(f -> f.endsWith(".java"))) {
            return new ReviewResult("", List.of(), true, "超范围：本切片只评审 Java diff。", false);
        }
        List<String> strippedAdded = parsed.added().stream()
                .map(String::strip).filter(s -> !s.isEmpty()).toList();
        List<String> strippedRemoved = parsed.removed().stream()
                .map(String::strip).filter(s -> !s.isEmpty()).toList();
        if (!strippedAdded.isEmpty() && strippedAdded.equals(strippedRemoved)) {
            return new ReviewResult("无实质评审意见", List.of(), false,
                    "仅格式 / 缩进改动，无实质评审意见。", false);
        }
        boolean commentOnly = !strippedAdded.isEmpty() && strippedAdded.stream().allMatch(
                ln -> ln.startsWith("//") || ln.startsWith("/*")
                        || ln.startsWith("*") || ln.startsWith("*/"));
        if (commentOnly) {
            return new ReviewResult("无实质评审意见", List.of(), false,
                    "仅注释改动，无实质评审意见。", false);
        }

        List<ReviewComment> comments = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        List<DiffChunker.Chunk> chunks = DiffChunker.chunk(parsed);
        for (int idx = 0; idx < chunks.size(); idx++) {
            DiffChunker.Chunk chunk = chunks.get(idx);
            String where = chunk.file() + "#chunk" + (idx + 1);
            String text = String.join("\n", chunk.lines());
            // Security lane.
            if ((text.contains("executeQuery") || text.contains("executeUpdate"))
                    && SQL_CONCAT.matcher(text).find()
                    && !text.contains("PreparedStatement")) {
                String off = chunk.lines().stream()
                        .filter(ln -> SQL_CONCAT.matcher(ln).find())
                        .findFirst().orElse("").strip();
                emit(comments, seen, new ReviewComment("high", "security", "sql-injection",
                        where, "字符串拼接 SQL，存在注入风险。",
                        "改用 PreparedStatement + 占位符 + set 参数，禁止拼接用户输入。"),
                        "sql-injection|" + off.replaceAll("\\s+", ""));
            }
            Matcher secret = SECRET.matcher(text);
            while (secret.find()) {
                String value = secret.group(2);
                if (value != null && !value.contains("${")
                        && !value.equals("***") && !value.equals("xxx")) {
                    // The literal secret is never put into the comment.
                    emit(comments, seen, new ReviewComment("high", "security",
                            "hardcoded-secret", where, "代码里硬编码了密钥。",
                            "把密钥移到环境变量或密钥管理服务，不要写进代码和仓库。"),
                            "hardcoded-secret|" + chunk.file());
                }
            }
            // Correctness lane, suppressed by an explicit guard for the
            // same variable in the same chunk.
            Matcher call = NULL_CALL.matcher(text);
            while (call.find()) {
                String var = call.group(1);
                boolean guarded = text.contains(var + " != null")
                        || text.contains(var + " == null")
                        || text.contains("Objects.requireNonNull(" + var + ")");
                if (!guarded) {
                    emit(comments, seen, new ReviewComment("medium", "correctness",
                            "null-check", where, "未判空就调用 " + var + " 的方法，可能空指针。",
                            "调用前判空，或用 Objects.requireNonNull(" + var + ") 明确约定。"),
                            "null-check|" + var);
                }
            }
            // Maintainability lane.
            if (EMPTY_CATCH.matcher(text).find()) {
                emit(comments, seen, new ReviewComment("medium", "maintainability",
                        "empty-catch", where, "空 catch 吞掉了异常，失败时无迹可查。",
                        "至少记录日志并按业务语义处理或向上抛，不要空 catch。"),
                        "empty-catch|" + chunk.file());
            }
            for (String line : chunk.lines()) {
                if (line.length() > 120) {
                    emit(comments, seen, new ReviewComment("low", "maintainability",
                            "long-line", where, "单行超过 120 字符，可读性差。",
                            "拆行或抽取常量 / 方法，控制单行长度。"),
                            "long-line|" + line.strip().substring(0, Math.min(60, line.strip().length()))
                                    .replaceAll("\\s+", ""));
                }
            }
        }
        comments.sort(Comparator.comparingInt((ReviewComment c) -> severityRank(c.severity()))
                .thenComparing(ReviewComment::rule));
        return new ReviewResult("共 " + comments.size() + " 条评论，需人工确认后才能合入。",
                comments, false, "", false);
    }

    private static void emit(List<ReviewComment> comments, Set<String> seen,
                             ReviewComment comment, String key) {
        if (seen.add(key)) {
            comments.add(comment);
        }
    }
}
