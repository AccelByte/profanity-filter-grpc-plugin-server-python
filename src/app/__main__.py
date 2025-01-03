# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import asyncio
import json
import logging

from enum import IntFlag
from pathlib import Path

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

from app.services.profanity_service import AsyncProfanityFilterService

DEFAULT_APP_PORT: int = 6565


class PermissionAction(IntFlag):
    CREATE = 0b0001
    READ = 0b0010
    UPDATE = 0b0100
    DELETE = 0b1000


async def main(**kwargs) -> None:
    env = Env(
        eager=kwargs.get("env_eager", True),
        expand_vars=kwargs.get("env_expand_vars", False),
    )
    env.read_env(
        path=kwargs.get("env_path", None),
        recurse=kwargs.get("env_recurse", True),
        verbose=kwargs.get("env_verbose", False),
        override=kwargs.get("env_override", False),
    )

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

            resource = env("RESOURCE", None)
            action = env.int("ACTION", None)

            config = MyConfigRepository(base_url, client_id, client_secret, namespace)
            token = InMemoryTokenRepository()
            sdk = AccelByteSDK()
            sdk.initialize(options={"config": config, "token": token})
            result, error = login_client(sdk=sdk)
            if error:
                raise Exception(str(error))
            sdk.timer = LoginClientTimer(2880, repeats=-1, autostart=True, sdk=sdk)
            token_validator = CachingTokenValidator(sdk)
            auth_server_interceptor = AuthorizationServerInterceptor(
                token_validator=token_validator,
                resource=resource,
                action=action,
                namespace=namespace,
            )
            opts.append(AppGRPCInterceptorOpt(auth_server_interceptor))

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
