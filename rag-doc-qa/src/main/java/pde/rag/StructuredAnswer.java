package pde.rag;

import java.util.List;

/** Structured answer returned by POST /api/qa. Always parseable, even on refusal. */
public record StructuredAnswer(
        String answer,
        List<String> citations,
        boolean refused,
        String reason) {
    public StructuredAnswer {
        if (citations == null) {
            citations = List.of();
        }
    }
}
