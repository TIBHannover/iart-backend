import logging

from rest_framework.views import exception_handler


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
  response = exception_handler(exc, context)
  logger.exception(exc)

  if response is not None:
    response.data['status_code'] = response.status_code

  return response
