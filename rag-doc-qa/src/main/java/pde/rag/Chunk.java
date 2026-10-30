package pde.rag;

/** One ingested chunk. id is "source-file#heading" and must exist in data/chunks.json. */
public record Chunk(String id, String source, String heading, String text) {
}
