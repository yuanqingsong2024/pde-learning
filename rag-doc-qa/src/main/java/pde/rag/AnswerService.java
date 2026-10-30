package pde.rag;

import java.util.List;

/**
 * Answer logic for the slice.
 *
 * - Out-of-scope / secret / internal-data questions are refused before retrieval.
 * - If the best chunk scores below THRESHOLD, refuse instead of hallucinating.
 * - Otherwise answer only from the retrieved chunks and cite their ids.
 *
 * The template answer below is the offline stand-in for the generation step.
 * In production, replace it with Spring AI ChatClient structured output using
 * prompts/qa-answer.md, keeping the same refusal and citation rules.
 */
public class AnswerService {

    /** Minimum best-chunk score for an answer; below this, refuse. */
    public static final double THRESHOLD = 0.20;

    private static final List<String> DENY_HINTS =
            List.of("密钥", "密码", "api key", "apikey", "内部薪资", "薪资", "客户隐私", "身份证");

    private final ChunkStore store;

    public AnswerService(ChunkStore store) {
        this.store = store;
    }

    public StructuredAnswer ask(String question) {
        if (question == null || question.isBlank()) {
            return new StructuredAnswer("", List.of(), true, "问题为空，无法回答。");
        }
        String lower = question.toLowerCase();
        for (String hint : DENY_HINTS) {
            if (lower.contains(hint)) {
                return new StructuredAnswer("", List.of(), true,
                        "该问题涉及敏感或内部信息，不在公开文档语料范围内，已拒答。");
            }
        }
        List<Chunk> top = store.retrieve(question, 3);
        if (top.isEmpty() || store.score(question, top.get(0)) < THRESHOLD) {
            return new StructuredAnswer("", List.of(), true,
                    "语料中没有足够证据回答该问题，已拒答，不编造答案。");
        }
        // Grounding check for specific-value questions: a retrieval score alone
        // cannot tell whether the chunk actually contains the asked-for value.
        // If the question asks for a version number / amount, the top chunk
        // must contain a decimal version-like pattern, otherwise refuse.
        if ((question.contains("版本号") || question.contains("是多少"))
                && !top.get(0).text().matches("(?s).*\\d+\\.\\d+.*")) {
            return new StructuredAnswer("", List.of(), true,
                    "语料中没有给出该具体数值，已拒答，不编造答案。");
        }
        List<String> citations = top.stream().map(Chunk::id).toList();
        String answer = "根据检索到的文档片段：\n" + top.get(0).text().strip();
        return new StructuredAnswer(answer, citations, false, "");
    }
}
