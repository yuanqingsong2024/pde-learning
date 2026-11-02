package pde.review;

import java.util.ArrayList;
import java.util.List;

/**
 * Splits a unified diff into per-file chunks of at most 40 added lines.
 * Removed lines are kept for the format-only check in ReviewService.
 */
public class DiffChunker {

    public static final int CHUNK_LINES = 40;

    public record ParsedDiff(List<String> files, List<String> added, List<String> removed) {
    }

    public record Chunk(String file, List<String> lines) {
    }

    public static ParsedDiff parse(String diff) {
        List<String> files = new ArrayList<>();
        List<String> added = new ArrayList<>();
        List<String> removed = new ArrayList<>();
        for (String line : diff.split("\n")) {
            if (line.startsWith("+++ ")) {
                files.add(line.substring(4).strip().replaceFirst("^b/", ""));
            } else if (line.startsWith("+") && !line.startsWith("+++")) {
                added.add(line.substring(1));
            } else if (line.startsWith("-") && !line.startsWith("---")) {
                removed.add(line.substring(1));
            }
        }
        return new ParsedDiff(files, added, removed);
    }

    public static List<Chunk> chunk(ParsedDiff parsed) {
        List<Chunk> out = new ArrayList<>();
        String file = parsed.files().isEmpty() ? "unknown" : parsed.files().get(0);
        for (int i = 0; i < parsed.added().size(); i += CHUNK_LINES) {
            out.add(new Chunk(file, parsed.added().subList(
                    i, Math.min(i + CHUNK_LINES, parsed.added().size()))));
        }
        if (out.isEmpty()) {
            out.add(new Chunk(file, List.of()));
        }
        return out;
    }
}
