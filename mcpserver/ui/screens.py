from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class UserInputScreen(ModalScreen[str]):
    """
    A modal dialog that asks the user for text input.
    Returns the string entered when submitted.
    """

    CSS = """
    UserInputScreen {
        align: center middle;
    }

    #dialog {
        grid-size: 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 3;
        padding: 0 1;
        width: 60;
        height: 11;
        border: thick $background 80%;
        background: $surface;
    }

    #question {
        column-span: 2;
        height: 1fr;
        width: 1fr;
        content-align: center middle;
    }

    Input {
        column-span: 2;
    }

    Button {
        width: 100%;
    }
    """

    def __init__(self, question: str):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question, id="question")
            yield Input(placeholder="Type your answer here...", id="input")
            with Horizontal():
                yield Button("Submit", variant="primary", id="submit")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit":
            input_widget = self.query_one(Input)
            value = input_widget.value
            self.dismiss(value)
        else:
            self.dismiss(None)  # Cancelled

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """
        Allow pressing Enter to submit.
        """
        self.dismiss(event.value)
