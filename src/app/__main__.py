# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import asyncio
import logging

from enum import IntFlag

from environs import Env

from app.proto.profanityFilter_pb2_grpc import (
    add_ProfanityFilterServiceServicer_to_server,
)

from accelbyte_grpc_plugin import App, AppGRPCInterceptorOpt, AppGRPCServiceOpt
from accelbyte_grpc_plugin.interceptors.authorization import (
    AuthorizationServerInterceptor,
)
from accelbyte_grpc_plugin.interceptors.logging import (
    DebugLoggingServerInterceptor,
)
from accelbyte_grpc_plugin.interceptors.metrics import (
    MetricsServerInterceptor,
)
from accelbyte_grpc_plugin.opts.grpc_health_checking import GRPCHealthCheckingOpt
from accelbyte_grpc_plugin.opts.grpc_reflection import GRPCReflectionOpt
from accelbyte_grpc_plugin.opts.prometheus import PrometheusOpt
from accelbyte_grpc_plugin.opts.zipkin import ZipkinOpt

from accelbyte_grpc_plugin.utils import create_env, instrument_sdk_http_client

from app.services.profanity_service import AsyncProfanityFilterService

DEFAULT_APP_PORT: int = 6565


class PermissionAction(IntFlag):
    CREATE = 0b0001
    READ = 0b0010
    UPDATE = 0b0100
    DELETE = 0b1000


async def main(**kwargs) -> None:
    env = create_env(**kwargs)

    port: int = env.int("PORT", DEFAULT_APP_PORT)

    opts = []
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    with env.prefixed("AB_"):
        base_url = env("BASE_URL", "https://demo.accelbyte.io")
        client_id = env("CLIENT_ID", None)
        client_secret = env("CLIENT_SECRET", None)
        namespace = env("NAMESPACE", "accelbyte")

    with env.prefixed(prefix="ENABLE_"):
        if env.bool("PROMETHEUS", True):
            opts.append(PrometheusOpt())
        if env.bool("HEALTH_CHECKING", True):
            opts.append(GRPCHealthCheckingOpt())
        if env.bool("REFLECTION", True):
            opts.append(GRPCReflectionOpt())
        if env.bool("ZIPKIN", True):
            opts.append(ZipkinOpt())

    with env.prefixed(prefix="PLUGIN_GRPC_SERVER_AUTH_"):
        if env.bool("ENABLED", False):
            from accelbyte_py_sdk import AccelByteSDK
            from accelbyte_py_sdk.core import MyConfigRepository, InMemoryTokenRepository
            from accelbyte_py_sdk.token_validation.caching import CachingTokenValidator
            from accelbyte_py_sdk.services.auth import login_client, LoginClientTimer

            config = MyConfigRepository(base_url, client_id, client_secret, namespace)
            token = InMemoryTokenRepository()

            sdk = AccelByteSDK()
            sdk.initialize(options={"config": config, "token": token})

            instrument_sdk_http_client(sdk=sdk, logger=logger)

            result, error = login_client(sdk=sdk)
            if error:
                raise Exception(str(error))

            sdk.timer = LoginClientTimer(2880, repeats=-1, autostart=True, sdk=sdk)

            opts.opts.append(
                AppGRPCInterceptorOpt(
                    interceptor=AuthorizationServerInterceptor(
                        namespace=namespace,
                        token_validator=CachingTokenValidator(sdk=sdk),
                    )
                )
            )

    if env.bool("PLUGIN_GRPC_SERVER_LOGGING_ENABLED", False):
        opts.append(AppGRPCInterceptorOpt(DebugLoggingServerInterceptor(logger)))

    if env.bool("PLUGIN_GRPC_SERVER_METRICS_ENABLED", True):
        opts.append(AppGRPCInterceptorOpt(MetricsServerInterceptor()))

    # register Filter Service
    opts.append(
        AppGRPCServiceOpt(
            AsyncProfanityFilterService(
                logger=logger,
            ),
            AsyncProfanityFilterService.full_name,
            add_ProfanityFilterServiceServicer_to_server,
        )
    )

    await App(port, env, opts=opts).run()


if __name__ == "__main__":
    asyncio.run(main())
