# Copyright (c) 2023 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

from unittest import IsolatedAsyncioTestCase

import grpc.aio

from app.proto.profanityFilter_pb2 import (
    ExtendProfanityValidationRequest,
    ExtendProfanityValidationResponse,
)
from app.proto.profanityFilter_pb2_grpc import (
    ProfanityFilterServiceStub,
    add_ProfanityFilterServiceServicer_to_server,
)
from app.services.profanity_service import AsyncProfanityFilterService

from accelbyte_grpc_plugin_tests import create_server


class AsyncProfanityFilterServiceTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.service = AsyncProfanityFilterService(
            extra_profane_word_dictionaries={"en": {"feck"}}
        )

    async def test_connection(self):
        addr = "localhost:50051"
        server = create_server(addr, [])
        add_ProfanityFilterServiceServicer_to_server(self.service, server)

        await server.start()

        try:
            async with grpc.aio.insecure_channel(addr) as channel:
                # assert
                stub = ProfanityFilterServiceStub(channel)
                request = ExtendProfanityValidationRequest()

                # act
                response = await stub.Validate(request)

                # assert
                self.assertIsNotNone(response)
        finally:
            await server.stop(grace=None)

    async def test_validate(self):
        # arrange 1
        request = ExtendProfanityValidationRequest()
        request.value = "feck"

        # act 1
        response = await self.service.Validate(request, None)

        # assert 1
        self.assertIsNotNone(response)
        self.assertIsInstance(response, ExtendProfanityValidationResponse)
        self.assertTrue(response.isProfane)

        # arrange 2
        request = ExtendProfanityValidationRequest()
        request.value = "hello"

        # act 2
        response = await self.service.Validate(request, None)

        # assert 2
        self.assertIsNotNone(response)
        self.assertIsInstance(response, ExtendProfanityValidationResponse)
        self.assertFalse(response.isProfane)
