import os
from typing import Dict, Optional, Union

from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_core.language_models import BaseChatModel
from deepeval.key_handler import KeyValues, KEY_FILE_HANDLER
from deepeval.models.base import DeepEvalBaseModel
from deepeval.chat_completion.retry import retry_with_exponential_backoff

valid_gpt_models = [
    "gpt-4-1106-preview",
    "gpt-4",
    "gpt-4-32k",
    "gpt-4-0613",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
]

default_gpt_model = "gpt-4-1106-preview"


class GPTModel(DeepEvalBaseModel):
    def __init__(
        self,
        model: Optional[Union[str, BaseChatModel]] = None,
        model_kwargs: Dict = {},
        *args,
        **kwargs,
    ):
        model_name = None
        custom_model = None
        if isinstance(model, str):
            model_name = model
            if model_name not in valid_gpt_models:
                raise ValueError(
                    f"Invalid model. Available GPT models: {', '.join(model for model in valid_gpt_models)}"
                )
            else:
                model_name = default_gpt_model
        elif isinstance(model, BaseChatModel):
            custom_model = model

        self.custom_model = custom_model
        self.model_kwargs = model_kwargs
        super().__init__(model_name, *args, **kwargs)

    def load_model(self):
        if self.custom_model:
            return self.custom_model

        if self.should_use_azure_openai():
            openai_api_key = KEY_FILE_HANDLER.fetch_data(
                KeyValues.AZURE_OPENAI_API_KEY
            )

            openai_api_version = KEY_FILE_HANDLER.fetch_data(
                KeyValues.OPENAI_API_VERSION
            )
            azure_deployment = KEY_FILE_HANDLER.fetch_data(
                KeyValues.AZURE_DEPLOYMENT_NAME
            )
            azure_endpoint = KEY_FILE_HANDLER.fetch_data(
                KeyValues.AZURE_OPENAI_ENDPOINT
            )

            model_version = KEY_FILE_HANDLER.fetch_data(
                KeyValues.AZURE_MODEL_VERSION
            )

            if model_version is None:
                model_version = ""

            return AzureChatOpenAI(
                openai_api_version=openai_api_version,
                azure_deployment=azure_deployment,
                azure_endpoint=azure_endpoint,
                openai_api_key=openai_api_key,
                model_version=model_version,
            )

        return ChatOpenAI(
            model_name=self.model_name, model_kwargs=self.model_kwargs
        )

    @retry_with_exponential_backoff
    def _call(self, prompt: str):
        chat_model = self.load_model()
        return chat_model.invoke(prompt)

    def should_use_azure_openai(self):
        value = KEY_FILE_HANDLER.fetch_data(KeyValues.USE_AZURE_OPENAI)
        return value.lower() == "yes" if value is not None else False
