from zocalo.trigger import Trigger, TriggerResponse


class test(Trigger):
    name = "TestTrigger"

    def run(self):
        self._jobid = 12
        # self._add_job("test processing", "myrecipe")
        # params = {
        #     "param1": 42
        # }
        # self._add_parameters(params)

        self._trigger_job({"testid": 42})

        return TriggerResponse(success=True, return_value=self._jobid)
