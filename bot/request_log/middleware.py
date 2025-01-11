import logging
import time
import structlog

# Настройка стандартного логгера Python
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[
        logging.FileHandler("./bot/request_log/logs.json", encoding="utf-8"),
        #logging.StreamHandler(),  # Вывод в консоль
    ]
)

# Настройка Structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=True),  # Добавление временной метки
        structlog.processors.JSONRenderer(ensure_ascii=False, indent=4, sort_keys=True)  # Формат JSON
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),  # Используем стандартный логгер Python
    cache_logger_on_first_use=True
)

logger = structlog.get_logger()


class RequestLogMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_request(self, request):
        request.start_time = time.time()

    def process_response(self, request, response):
        try:
            if response['content-type'] == 'application/json':
                if getattr(response, 'streaming', False):
                    response_body = '<<<Streaming>>>'
                else:
                    response_body = response.data
            else:
                response_body = '<<<Not JSON>>>'

            request_data = request.request.data
            log_data = {
                'request_data': request_data,
                'response_status': response.status_code,
                'response_body': response_body,
                'run_time': time.time() - request.start_time,
            }

            logger.info("Request log", **log_data)

        except Exception as e:
            logger.error("Error while logging", error=str(e))

        return response
