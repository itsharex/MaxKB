# coding=utf-8
"""
    @project: MaxKB
    @Author：虎
    @file： base_function_lib_node.py
    @date：2024/8/8 17:49
    @desc:
"""
import json
import time
from typing import Dict

from django.db.models import QuerySet

from application.flow.i_step_node import NodeResult
from application.flow.step_node.function_lib_node.i_function_lib_node import IFunctionLibNode
from common.exception.app_exception import AppApiException
from common.util.function_code import FunctionExecutor
from function_lib.models.function import FunctionLib
from smartdoc.const import CONFIG

function_executor = FunctionExecutor(CONFIG.get('SANDBOX'))


def write_context(step_variable: Dict, global_variable: Dict, node, workflow):
    if step_variable is not None:
        for key in step_variable:
            node.context[key] = step_variable[key]
        if workflow.is_result() and 'result' in step_variable:
            result = step_variable['result'] + '\n'
            yield result
            workflow.answer += result
    node.context['run_time'] = time.time() - node.context['start_time']


def get_field_value(debug_field_list, name, is_required):
    result = [field for field in debug_field_list if field.get('name') == name]
    if len(result) > 0:
        return result[-1]['value']
    if is_required:
        raise AppApiException(500, f"{name}字段未设置值")
    return None


def convert_value(name: str, value, _type, is_required, source, node):
    if not is_required and value is None:
        return None
    if source == 'reference':
        value = node.workflow_manage.get_reference_field(
            value[0],
            value[1:])
        return value
    try:
        if _type == 'int':
            return int(value)
        if _type == 'float':
            return float(value)
        if _type == 'dict':
            return json.loads(value)
        if _type == 'array':
            return json.loads(value)
        return value
    except Exception as e:
        raise AppApiException(500, f'字段:{name}类型:{_type}值:{value}类型转换错误')


class BaseFunctionLibNodeNode(IFunctionLibNode):
    def execute(self, function_lib_id, input_field_list, **kwargs) -> NodeResult:
        function_lib = QuerySet(FunctionLib).filter(id=function_lib_id).first()
        params = {field.get('name'): convert_value(field.get('name'), field.get('value'), field.get('type'),
                                                   field.get('is_required'),
                                                   field.get('source'), self)
                  for field in
                  [{'value': get_field_value(input_field_list, field.get('name'), field.get('is_required'),
                                             ), **field}
                   for field in
                   function_lib.input_field_list]}
        self.context['params'] = params
        result = function_executor.exec_code(function_lib.code, params)
        return NodeResult({'result': result}, {}, _write_context=write_context)

    def get_details(self, index: int, **kwargs):
        return {
            'name': self.node.properties.get('stepName'),
            "index": index,
            "result": self.context.get('result'),
            "params": self.context.get('params'),
            'run_time': self.context.get('run_time'),
            'type': self.node.type,
            'status': self.status,
            'err_message': self.err_message
        }