package pde.rag;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Slice retrieval: IDF-weighted token overlap over ingested chunks.
 *
 * Why IDF: plain overlap lets one long page section (which contains almost
 * every common character) win every query. Weighting a token by
 * ln(N / document-frequency) + 1 makes rare, discriminating tokens
 * (code-review, Schema, POG, SQL) count more than common characters, and
 * tokens absent from the corpus raise the denominator, which is what makes
 * no-answer questions fall below the refusal threshold.
 *
 * Production evolution: replace this with vector retrieval + hybrid retrieval
 * + reranking. The interface (retrieve top-k chunks with scores) stays the same,
 * so the controller, the structured answer and the eval set do not change.
 */
public class ChunkStore {

    private final List<Chunk> chunks;
    private final List<Set<String>> chunkTokens;
    private final Map<String, Double> idf = new HashMap<>();

    public ChunkStore(List<Chunk> chunks) {
        this.chunks = List.copyOf(chunks);
        this.chunkTokens = new ArrayList<>();
        for (Chunk c : this.chunks) {
            chunkTokens.add(tokens(c.text() + " " + c.heading() + " " + c.source()));
        }
        Set<String> all = new HashSet<>();
        chunkTokens.forEach(all::addAll);
        int n = Math.max(chunks.size(), 1);
        for (String token : all) {
            long df = chunkTokens.stream().filter(t -> t.contains(token)).count();
            idf.put(token, Math.log((double) n / Math.max(df, 1)) + 1.0);
        }
    }

    public List<Chunk> chunks() {
        return chunks;
    }

    private double idf(String token) {
        return idf.getOrDefault(token, Math.log(Math.max(chunks.size(), 1)) + 1.0);
    }

    /** IDF-weighted shared-token score in [0, 1]. */
    public double score(String question, Chunk chunk) {
        Set<String> q = tokens(question);
        if (q.isEmpty()) {
            return 0.0;
        }
        int index = chunks.indexOf(chunk);
        Set<String> c = index >= 0 ? chunkTokens.get(index)
                : tokens(chunk.text() + " " + chunk.heading() + " " + chunk.source());
        double denom = q.stream().mapToDouble(this::idf).sum();
        double shared = q.stream().filter(c::contains).mapToDouble(this::idf).sum();
        return denom == 0 ? 0.0 : shared / denom;
    }

    public List<Chunk> retrieve(String question, int topK) {
        List<Chunk> sorted = new ArrayList<>(chunks);
        sorted.sort(Comparator.comparingDouble((Chunk c) -> score(question, c)).reversed());
        return sorted.subList(0, Math.min(topK, sorted.size()));
    }

    static Set<String> tokens(String text) {
        // English words + Chinese bigrams. Whole-phrase tokens are useless for
        // Chinese (a question is one long token), and single characters are
        // too noisy (every long section matches them). Bigrams are the
        // discriminating unit: '治理清单' matches the POG chunk, '代码评审'
        // matches the code-review chunk.
        Set<String> out = new HashSet<>();
        for (String part : text.toLowerCase().split("[^a-z0-9_]+")) {
            if (!part.isBlank()) {
                out.add(part);
            }
        }
        StringBuilder run = new StringBuilder();
        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (ch >= 0x4E00 && ch <= 0x9FFF) {
                run.append(ch);
            } else {
                addBigrams(out, run.toString());
                run.setLength(0);
            }
        }
        addBigrams(out, run.toString());
        return out;
    }

    private static void addBigrams(Set<String> out, String run) {
        for (int i = 0; i + 1 < run.length(); i++) {
            out.add(run.substring(i, i + 2));
        }
    }
}
