# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function

import logging


class BaseWrapper(object):
    def set_recipe_wrapper(self, recwrap):
        self.recwrap = recwrap

    def prepare(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("starting", payload)

    def update(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("updates", payload)

    def done(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("completed", payload)

    def success(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("success", payload)

    def failure(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("failure", str(payload))

    def run(self):
        raise NotImplementedError()

    def record_result_individual_file(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-individual-file", payload)

    def record_result_all_files(self, payload=""):
        if getattr(self, "recwrap", None):
            self.recwrap.send_to("result-all-files", payload)


class DummyWrapper(BaseWrapper):
    def run(self):
        logging.getLogger("dlstbx.zocalo.wrapper.DummyWrapper").info(
            "This is a dummy wrapper that simply waits for a minute."
        )
        import time

        time.sleep(10)
        self.status_thread.taskname += " (still running)"
        time.sleep(50)
        return True
