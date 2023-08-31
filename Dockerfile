FROM public.ecr.aws/lambda/python:3.8
RUN pip3 install 'urllib3<2.0' requests slackweb pandas
RUN pip3 install pinnacle

COPY lambda_function.py ${LAMBDA_TASK_ROOT}
COPY pinnacle_client.py ${LAMBDA_TASK_ROOT}
CMD [ "lambda_function.handler" ]