class DiagnosticSession:
    def __init__(self):
        self.topic = None
        self.answers = {}
        self.current_question = 0

    def start(self, topic):
        self.topic = topic
        self.answers = {}
        self.current_question = 0

    def save_answer(self, question, answer):
        self.answers[question] = answer

    def get_answers(self):
        return self.answers

    def clear(self):
        self.topic = None
        self.answers = {}
        self.current_question = 0
