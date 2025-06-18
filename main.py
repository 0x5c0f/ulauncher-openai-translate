import json
import logging
import os
from openai import OpenAI

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

# Initialize logger
logger = logging.getLogger(__name__)

class OpenAITranslateExtension(Extension):

    def __init__(self):
        super(OpenAITranslateExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesEventListener())
        self.openai_client = None

class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        items = []
        query = event.get_argument()

        # 获取配置参数
        openai_api_key = extension.preferences.get("openai_api_key")
        base_url = extension.preferences.get("base_url", "").strip()
        custom_prompt = extension.preferences.get("custom_prompt", "").strip()
        model_name = extension.preferences.get("model_name", "gpt-4o-mini").strip()
        
        if not openai_api_key:
            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name='OpenAI API Key Missing',
                                             description='Please set your OpenAI API Key in Ulauncher preferences.',
                                             highlightable=False))
            return RenderResultListAction(items)

        # 初始化或更新 OpenAI 客户端
        if extension.openai_client is None or self._need_client_update(extension, base_url):
            try:
                client_kwargs = {"api_key": openai_api_key}
                if base_url:
                    client_kwargs["base_url"] = base_url
                extension.openai_client = OpenAI(**client_kwargs)
                extension._current_base_url = base_url  # 记录当前使用的 base_url
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                items.append(ExtensionResultItem(icon='images/icon.png',
                                                 name='Error initializing OpenAI client',
                                                 description=f'{e}',
                                                 highlightable=False))
                return RenderResultListAction(items)

        if not query:
            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name='Type something to translate',
                                             description='Enter text to translate using OpenAI',
                                             highlightable=False))
            return RenderResultListAction(items)

        try:
            # 直接使用整个查询作为要翻译的文本
            text_to_translate = query.strip()

            if not text_to_translate:
                items.append(ExtensionResultItem(icon='images/icon.png',
                                                 name='Type something to translate',
                                                 description='Enter text to translate using OpenAI',
                                                 highlightable=False))
                return RenderResultListAction(items)

            # 构建消息
            messages = []
            
            # 添加系统消息
            if custom_prompt:
                messages.append({"role": "system", "content": custom_prompt})
            else:
                # 使用默认系统提示词
                default_system_prompt = "You are a useful translation assistant. Please translate my Chinese into English and translate all non-Chinese into Chinese. Everything I send you is content that needs translation; you only need to provide the translation results. The translation results should conform to Chinese language habits."
                messages.append({"role": "system", "content": default_system_prompt})
            
            # 添加用户消息（要翻译的文本）
            messages.append({"role": "user", "content": text_to_translate})
            
            # Call OpenAI API
            chat_completion = extension.openai_client.chat.completions.create(
                messages=messages,
                model=model_name,
            )
            translated_text = chat_completion.choices[0].message.content.strip()

            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name=translated_text,
                                             description='Press Enter to copy to clipboard',
                                             on_enter=CopyToClipboardAction(translated_text)))

        except Exception as e:
            logger.error(f"Error during translation: {e}")
            items.append(ExtensionResultItem(icon='images/icon.png',
                                             name='Error during translation',
                                             description=f'{e}\nCheck logs for details',
                                             highlightable=False))

        return RenderResultListAction(items)
    
    def _need_client_update(self, extension, new_base_url):
        """检查是否需要更新客户端（base_url 改变时）"""
        current_base_url = getattr(extension, '_current_base_url', None)
        return current_base_url != new_base_url

class PreferencesEventListener(EventListener):

    def on_event(self, event, extension):
        logger.info(f"Preferences updated: {extension.preferences}")
        openai_api_key = extension.preferences.get("openai_api_key")
        base_url = extension.preferences.get("base_url", "").strip()
        
        if openai_api_key:
            try:
                client_kwargs = {"api_key": openai_api_key}
                if base_url:
                    client_kwargs["base_url"] = base_url
                extension.openai_client = OpenAI(**client_kwargs)
                extension._current_base_url = base_url
            except Exception as e:
                logger.error(f"Error updating OpenAI client: {e}")
                extension.openai_client = None
        else:
            extension.openai_client = None

if __name__ == '__main__':
    OpenAITranslateExtension().run()