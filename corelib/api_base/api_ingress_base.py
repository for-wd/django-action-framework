from django.views.generic import View
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from corelib import APIAuth, config

import json


@method_decorator(csrf_exempt, name='dispatch')
class APIIngressBase(View):
    actions = {}

    def post(self, request, *args, **kwargs):
        # To check post data in JSON.
        data = self.json_load(self.request)
        if isinstance(data, HttpResponse):
            return data

        # validate 'action'
        action = data.get('action')
        if not action:
            return HttpResponse("ERROR: 'action' field is required.", status=400)
        if action not in self.actions:
            return HttpResponse(f"ERROR: illegal action: '{action}'", status=400)

        # authentication
        auth_token = data.get('auth_token')
        if action not in config.NO_AUTH_ACTIONS and config.AUTH_REQUIRED:
            auth = APIAuth()
            auth_result = auth.auth_by_token(auth_token) if auth_token else auth.auth_by_session(request.user)
            if not auth_result:
                return HttpResponse("ERROR: API authentication failed", status=401)

        # dispatch by action
        handler = self.actions[action](parameters=data, request=request)
        getattr(handler, action, lambda: HttpResponse("ERROR: method not accomplished by handler.", status=500))()

        # make HttpResponse
        if handler.result:
            response_data = {"result": "SUCCESS", "message": str(handler.message)}
            if handler.data is not None:
                response_data['data'] = handler.data
            if handler.data_total_length is not None:
                response_data['data_total_length'] = handler.data_total_length
        else:
            response_data = {"result": "FAILED", "message": str(handler.error_message)}

        return HttpResponse(json.dumps(response_data), content_type='application/json', status=handler.http_status)

    def get(self, request, *args, **kwargs):
        return HttpResponse("GET method is not allowed.", status=403)

    def json_load(self, request, decode_type='utf-8'):
        """
        To load json data from http request.body.
        If Not a JSON data, return ERROR.
        If data not a dict, return ERROR.
        """

        try:
            post_data = json.loads(request.body.decode(decode_type))
        except Exception:
            return HttpResponse("ERROR: To load json data failed.", status=400)

        if isinstance(post_data, dict):
            return post_data
        else:
            return HttpResponse("ERROR: Post data is not a dict.", status=400)
