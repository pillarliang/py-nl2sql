"""
Author: pillar
Date: 2024-08-30
Description: prompts
Note: Different languages should use prompts that are appropriate for that language.
"""

import json

from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
import os
from py_nl2sql.constants.type import LLMModel
from py_nl2sql.utilities.tools import batch_image_to_base64


class LLM:
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)  # temporarily using openai service

    def get_response(self, query: str):
        completion = self.client.chat.completions.create(
            model=LLMModel.Default.value,
            messages=[
                {"role": "user", "content": query},
            ],
        )
        return completion.choices[0].message.content

    def get_structured_response(self, query: str, response_format):
        completion = self.client.beta.chat.completions.parse(
            model=LLMModel.Default.value,
            # TODO: currently using a specific model, due to only lasted model support structured response
            messages=[
                {"role": "user", "content": query}
            ],
            response_format=response_format,
        )

        return json.loads(completion.choices[0].message.content)

    def get_multimodal_response(self, query: str, contexts):
        texts = contexts.get("texts", "")
        images = contexts.get("images", "")
        encoded_images = batch_image_to_base64(images)

        prompts = f"""
        Please answer the following query based on the provided context and image information, rather than prior knowledge. 
        If the context cannot answer the question, please return: 暂找不到相关问题，请重新提供问题。
        
        Question: {query}
        
        Context: {texts}
        """

        messages = [{"type": "text", "text": prompts}]
        for item in encoded_images:
            messages.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{item}"}})

        completion = self.client.chat.completions.create(
            model=LLMModel.GPT_4o_mini.value,
            messages=[
                {
                    "role": "user",
                    "content": messages
                },
            ],
        )
        return completion.choices[0].message.content

    @property
    def embedding_model(self):
        return OpenAIEmbeddings(api_key=self.api_key, base_url=self.base_url)

