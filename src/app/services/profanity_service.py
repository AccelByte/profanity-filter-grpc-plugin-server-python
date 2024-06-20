# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import json
from logging import Logger
from typing import Collection, Dict, List, Optional

from google.protobuf.json_format import MessageToDict
from better_profanity import profanity

from app.proto.profanityFilter_pb2 import (
    ExtendProfanityValidationResponse,
    DESCRIPTOR,
)
from app.proto.profanityFilter_pb2_grpc import ProfanityFilterServiceServicer


class AsyncProfanityFilterService(ProfanityFilterServiceServicer):
    full_name: str = DESCRIPTOR.services_by_name["ProfanityFilterService"].full_name

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        extra_profane_word_dictionaries: Optional[
            Dict[Optional[str], Collection[str]]
        ] = None,
        logger: Optional[Logger] = None,
    ) -> None:
        custom_words = [
            word
            for language, words in extra_profane_word_dictionaries.items()
            for word in words
        ]

        self.filter = profanity
        self.filter.add_censor_words(custom_words=custom_words)
        self.logger = logger

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
