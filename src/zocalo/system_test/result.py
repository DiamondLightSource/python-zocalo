import timeit

from junit_xml import TestCase


class Result(TestCase):
    def __init__(self):
        TestCase.__init__(self, None)

        self.name = None
        self.classname = None
        self.elapsed_sec = 0
        self.skipped_message = None  # first skipped message
        self.skipped_output = None  # skipped messages
        self.failure_message = None  # error message
        self.failure_output = None  # stack trace
        # to test for failure use is_failure()
        self.stdout = None  # standard output
        self.stderr = None  # standard error
        self.start_time = timeit.default_timer()

    def __repr__(self):
        if self.is_failure():
            status = "failure"
        elif self.is_error():
            status = "error"
        elif self.is_skipped():
            status = "skipped"
        else:
            status = "success"
        return f"<Result {self.classname}.{self.name} ({status})>"

    def update_timer(self):
        self.set_time(timeit.default_timer() - self.start_time)

    def append(self, result):
        self.update_timer()

        if self.failure_message is None:
            self.failure_message = result.failure_message
            # otherwise ignore new message

        if self.skipped_message is None:
            self.skipped_message = result.skipped_message
            # otherwise ignore new message

        if self.skipped_output is None:
            self.skipped_output = result.skipped_output
        elif result.skipped_output is not None:
            self.skipped_output = "\n".join(
                [self.skipped_output, result.skipped_output]
            )

        if self.stderr is None:
            self.stderr = result.stderr
        elif result.stderr is not None:
            self.stderr = "\n".join([self.stderr, result.stderr])

        if self.stdout is None:
            self.stdout = result.stdout
        elif result.stdout is not None:
            self.stdout = "\n".join([self.stdout, result.stdout])

        if self.failure_output is None:
            self.failure_output = result.failure_output
        elif result.failure_output is not None:
            self.failure_output = "\n".join(
                [self.failure_output, result.failure_output]
            )

    def log_message(self, text):
        self.update_timer()
        if self.stdout is None:
            self.stdout = text
        else:
            self.stdout = self.stdout + "\n" + text

    def log_skip(self, text):
        self.update_timer()
        self.add_skipped_info(message=text, output=text)

    def log_error(self, message, output=None):
        self.update_timer()
        self.add_error_info(message=message, output=output)
        if self.stderr is None:
            self.stderr = message
        else:
            self.stderr = self.stderr + "\n" + message

    def log_trace(self, text):
        self.update_timer()
        self.add_failure_info(message=text.split("\n")[0], output=text)

    def set_name(self, name):
        self.name = name

    def set_classname(self, classname):
        self.classname = classname

    def set_time(self, time):
        self.elapsed_sec = time

    def is_success(self):
        return not self.is_failure() and not self.is_error() and not self.is_skipped()
