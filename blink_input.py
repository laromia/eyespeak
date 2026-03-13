import time
from morse_translator import get_char_from_sequence

class BlinkInput:

    def __init__(self):

        self.current_morse = ""
        self.text = ""

        self.last_blink_time = time.time()

        self.char_pause = 2.0
        self.word_pause = 5.0

    def process_blink(self, blink_event):

        if blink_event is None:
            return

        if blink_event == "." or blink_event == "-":

            self.current_morse += blink_event
            self.last_blink_time = time.time()

        elif blink_event == "reset":

            self.text = ""
            self.current_morse = ""

        elif blink_event == "clear":

            self.current_morse = ""

    def update(self):

        now = time.time()
        time_since_last = now - self.last_blink_time

        if self.current_morse != "" and time_since_last > self.char_pause:

            char = get_char_from_sequence(self.current_morse)

            if char != "?":
                self.text += char

            self.current_morse = ""
            self.last_blink_time = now

        elif self.text != "" and time_since_last > self.word_pause:

            if not self.text.endswith(" "):
                self.text += " "

            self.last_blink_time = now