# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import json
from logging import Logger
from typing import Collection, Dict, List, Optional

from google.protobuf.json_format import MessageToDict

from better_profanity import profanity

from accelbyte_py_sdk import AccelByteSDK

from ..proto.profanityFilter_pb2 import (
    ExtendProfanityValidationResponse,
    DESCRIPTOR,
)
from ..proto.profanityFilter_pb2_grpc import ProfanityFilterServiceServicer


class AsyncProfanityFilterService(ProfanityFilterServiceServicer):
    full_name: str = DESCRIPTOR.services_by_name["ProfanityFilterService"].full_name

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        extra_profane_word_dictionaries: Optional[
            Dict[Optional[str], Collection[str]]
        ] = None,
        sdk: Optional[AccelByteSDK] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        censor_words = []
        if extra_profane_word_dictionaries:
            censor_words.extend(
                word
                for language, words in extra_profane_word_dictionaries.items()
                for word in words
            )
        else:
            censor_words.extend(self.get_default_censor_words())

        self.filter = profanity
        self.filter.add_censor_words(custom_words=censor_words)
        self.sdk = sdk
        self.logger = logger

    # noinspection PyMethodMayBeStatic
    def get_default_censor_words(self) -> List[str]:
        return ["bad", "ibad", "yourbad"]

    async def Validate(self, request, context):
        self.log_payload(f"{self.Validate.__name__} request: %s", request)
        response = ExtendProfanityValidationResponse()
        if self.filter.contains_profanity(request.value):
            response.isProfane = True
            response.message = "this contains banned words"
        self.log_payload(f"{self.Validate.__name__} response: %s", response)
        return response

    # noinspection PyShadowingBuiltins
    def log_payload(self, format: str, payload):
        if not self.logger:
            return
        payload_dict = MessageToDict(payload, preserving_proto_field_name=True)
        payload_json = json.dumps(payload_dict)
        self.logger.info(format % payload_json)
