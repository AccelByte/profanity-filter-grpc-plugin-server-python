# Copyright (c) 2025 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import asyncio
import logging
from logging import Logger
from typing import List, Optional

from environs import Env

from accelbyte_py_sdk.core import (
    AccelByteSDK,
    DictConfigRepository,
    InMemoryTokenRepository,
    HttpxHttpClient,
)
from accelbyte_py_sdk.services import auth as auth_service

from accelbyte_grpc_plugin import (
    App,
    AppOpt,
    AppGRPCInterceptorOpt,
    AppGRPCServiceOpt,
)
from accelbyte_grpc_plugin.utils import instrument_sdk_http_client

from .proto.profanityFilter_pb2_grpc import add_ProfanityFilterServiceServicer_to_server
from .services.profanity_service import AsyncProfanityFilterService
from .utils import create_env

DEFAULT_APP_PORT: int = 6565

DEFAULT_AB_BASE_URL: str = "https://test.accelbyte.io"
DEFAULT_AB_NAMESPACE: str = "accelbyte"

DEFAULT_ENABLE_HEALTH_CHECK: bool = True
DEFAULT_ENABLE_PROMETHEUS: bool = True
DEFAULT_ENABLE_REFLECTION: bool = True
DEFAULT_ENABLE_ZIPKIN: bool = True

DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ENABLED: bool = True
DEFAULT_PLUGIN_GRPC_SERVER_AUTH_RESOURCE: Optional[str] = None
DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ACTION: Optional[int] = None

DEFAULT_PLUGIN_GRPC_SERVER_LOGGING_ENABLED: bool = False
DEFAULT_PLUGIN_GRPC_SERVER_METRICS_ENABLED: bool = True


async def main(**kwargs) -> None:
    env = create_env(**kwargs)

    port: int = env.int("PORT", DEFAULT_APP_PORT)

    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    config = DictConfigRepository(dict(env.dump()))
    token = InMemoryTokenRepository()
    http = HttpxHttpClient()
    http.client.follow_redirects = True

    sdk = AccelByteSDK()
    sdk.initialize(
        options={
            "config": config,
            "token": token,
            "http": http,
        }
    )

    instrument_sdk_http_client(sdk=sdk, logger=logger)

    _, error = await auth_service.login_client_async(sdk=sdk)
    if error:
        raise Exception(str(error))

    sdk.timer = auth_service.LoginClientTimer(2880, repeats=-1, autostart=True, sdk=sdk)

    options = create_options(sdk=sdk, env=env, logger=logger)
    options.append(
        AppGRPCServiceOpt(
            service=AsyncProfanityFilterService(
                sdk=sdk,
                logger=logger,
            ),
            service_full_name=AsyncProfanityFilterService.full_name,
            add_service_func=add_ProfanityFilterServiceServicer_to_server,
        )
    )

    app = App(port=port, env=env, logger=logger, options=options)
    await app.run()


def create_options(sdk: AccelByteSDK, env: Env, logger: Logger) -> List[AppOpt]:
    options: List[AppOpt] = []

    with env.prefixed("AB_"):
        namespace = env.str("NAMESPACE", DEFAULT_AB_NAMESPACE)

    with env.prefixed("ENABLE_"):
        if env.bool("HEALTH_CHECK", env.bool("HEALTH_CHECKING", DEFAULT_ENABLE_HEALTH_CHECK)):
            from accelbyte_grpc_plugin.opts.grpc_health_checking import (
                GRPCHealthCheckingOpt,
            )

            options.append(GRPCHealthCheckingOpt())
        if env.bool("PROMETHEUS", DEFAULT_ENABLE_PROMETHEUS):
            from accelbyte_grpc_plugin.opts.prometheus import (
                PrometheusOpt
            )

            options.append(PrometheusOpt())
        if env.bool("REFLECTION", DEFAULT_ENABLE_REFLECTION):
            from accelbyte_grpc_plugin.opts.grpc_reflection import (
                GRPCReflectionOpt,
            )

            options.append(GRPCReflectionOpt())
        if env.bool("ZIPKIN", DEFAULT_ENABLE_ZIPKIN):
            from accelbyte_grpc_plugin.opts.zipkin import (
                ZipkinOpt
            )

            options.append(ZipkinOpt())

    with env.prefixed("PLUGIN_GRPC_SERVER_"):
        with env.prefixed("AUTH_"):
            if env.bool("ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ENABLED):
                from accelbyte_py_sdk.token_validation.caching import CachingTokenValidator
                from accelbyte_grpc_plugin.interceptors.authorization import AuthorizationServerInterceptor

                options.append(
                    AppGRPCInterceptorOpt(
                        interceptor=AuthorizationServerInterceptor(
                            token_validator=CachingTokenValidator(sdk=sdk),
                            resource=env.str(
                                "RESOURCE", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_RESOURCE
                            ),
                            action=env.int(
                                "ACTION", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ACTION
                            ),
                            namespace=namespace,
                        )
                    )
                )
        if env.bool("LOGGING_ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_LOGGING_ENABLED):
            from accelbyte_grpc_plugin.interceptors.logging import (
                DebugLoggingServerInterceptor,
            )

            options.append(
                AppGRPCInterceptorOpt(
                    interceptor=DebugLoggingServerInterceptor(logger=logger)
                )
            )

        if env.bool("METRICS_ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_METRICS_ENABLED):
            from accelbyte_grpc_plugin.interceptors.metrics import (
                MetricsServerInterceptor,
            )

            options.append(
                AppGRPCInterceptorOpt(interceptor=MetricsServerInterceptor())
            )

    return options


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
