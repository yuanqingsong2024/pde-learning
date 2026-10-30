package pde.rag;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/** POST /api/qa — body: {"question": "..."}; response: StructuredAnswer. */
@RestController
public class QueryController {

    private final AnswerService answerService;

    public QueryController(AnswerService answerService) {
        this.answerService = answerService;
    }

    public record QueryRequest(String question) {
    }

    @PostMapping("/api/qa")
    public StructuredAnswer ask(@RequestBody QueryRequest request) {
        return answerService.ask(request.question());
    }
}
