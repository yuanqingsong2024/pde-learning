package pde.rag;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Spring Boot entry point. The chunk file is produced by tools/ingest.py
 * (data/chunks.json) and loaded at startup; no model key is read from code.
 *
 * Spring AI wiring (production step, not exercised in the offline eval):
 * inject a ChatClient built from the configured model, pass prompts/qa-answer.md
 * plus the retrieved chunks as context, and request StructuredAnswer as the
 * structured-output type. Keep the refusal and citation rules in AnswerService
 * as the gate around that call: if the model output cites a chunk id that is
 * not in the retrieved set, reject it and refuse.
 */
@SpringBootApplication
public class RagDocQaApplication {

    public static void main(String[] args) {
        SpringApplication.run(RagDocQaApplication.class, args);
    }

    @Bean
    public ChunkStore chunkStore() throws IOException {
        // Minimal JSON loading for the slice format: [{"id":..,"source":..,
        // "heading":..,"text":..}]. A production service should use Jackson.
        String json = Files.readString(Path.of("data/chunks.json"));
        List<Chunk> chunks = new ArrayList<>();
        for (String obj : splitObjects(json)) {
            chunks.add(new Chunk(
                    field(obj, "id"), field(obj, "source"),
                    field(obj, "heading"), field(obj, "text")));
        }
        return new ChunkStore(chunks);
    }

    @Bean
    public AnswerService answerService(ChunkStore store) {
        return new AnswerService(store);
    }

    // --- tiny JSON helpers, only for this slice's flat chunk format ---
    private static List<String> splitObjects(String json) {
        List<String> out = new ArrayList<>();
        int depth = 0;
        int start = -1;
        boolean inString = false;
        for (int i = 0; i < json.length(); i++) {
            char c = json.charAt(i);
            if (c == '"' && json.charAt(i - 1) != '\\') {
                inString = !inString;
            }
            if (inString) {
                continue;
            }
            if (c == '{') {
                if (depth == 1) {
                    start = i;
                }
                depth++;
            } else if (c == '}') {
                depth--;
                if (depth == 1 && start >= 0) {
                    out.add(json.substring(start, i + 1));
                    start = -1;
                }
            }
        }
        return out;
    }

    private static String field(String obj, String name) {
        String key = "\"" + name + "\": \"";
        int i = obj.indexOf(key);
        if (i < 0) {
            return "";
        }
        int start = i + key.length();
        StringBuilder sb = new StringBuilder();
        for (int j = start; j < obj.length(); j++) {
            char c = obj.charAt(j);
            if (c == '\\' && j + 1 < obj.length()) {
                sb.append(obj.charAt(j + 1));
                j++;
            } else if (c == '"') {
                break;
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }
}
