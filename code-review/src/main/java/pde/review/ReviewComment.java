package pde.review;

/** One structured review comment. Never carries a secret literal. */
public record ReviewComment(String severity, String lane, String rule,
                            String where, String problem, String suggestion) {
}
