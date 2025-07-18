# Автоматическое удаление сообщений пользователя

## Обзор
Реализована функция автоматического удаления всех сообщений пользователя для поддержания чистоты диалога. Теперь все пользовательские сообщения автоматически удаляются после обработки.

## Особенности
- **Автоматическое удаление**: Все текстовые сообщения пользователя удаляются автоматически
- **Задержка для UX**: Сообщения удаляются с небольшой задержкой (0.5 сек) для лучшего пользовательского опыта
- **Сохранение функциональности**: Вся логика обработки сохраняется, удаляется только визуальный мусор
- **Безопасное удаление**: Ошибки удаления не влияют на работу бота

## Технические детали

### Изменения в коде

1. **`bot/handlers.py`**:
   - Добавлен `import asyncio`
   - Модифицирован `_handle_message()` для автоматического удаления
   - Добавлен метод `_delete_user_message_delayed()`
   - Убраны дублирующие вызовы удаления из всех методов обработки ввода

### Как это работает

```python
async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle general messages for registration flow."""
    chat_id = update.effective_chat.id
    message_text = update.message.text
    message_id = update.message.message_id
    
    # Автоматически удаляем сообщение пользователя с задержкой
    asyncio.create_task(self._delete_user_message_delayed(chat_id, message_id))
    
    # Продолжаем обработку как обычно...
```

### Метод отложенного удаления

```python
async def _delete_user_message_delayed(self, chat_id: int, message_id: int, delay: float = 0.5) -> None:
    """Delete user message with a small delay for better UX."""
    try:
        await asyncio.sleep(delay)
        await self._delete_message_safe(chat_id, message_id)
    except Exception as e:
        logger.debug(f"Error deleting user message {message_id} in chat {chat_id}: {e}")
```

## Результат

### До реализации:
```
User: Europe/Moscow
Bot: ✅ Time zone saved!
User: 08:00
Bot: ✅ Send time saved!
User: 5,6
Bot: ✅ Setup Complete!
```

### После реализации:
```
Bot: ✅ Time zone saved!
Bot: ✅ Send time saved!
Bot: ✅ Setup Complete!
```

## Преимущества

1. **Чистый интерфейс**: Пользователь видит только ответы бота
2. **Лучший UX**: Диалог выглядит профессионально и организованно
3. **Конфиденциальность**: Введенные данные не остаются видимыми
4. **Неинвазивность**: Задержка 0.5 сек позволяет пользователю видеть что его сообщение было получено

## Ограничения

- Сообщения старше 48 часов не могут быть удалены (ограничение Telegram API)
- Работает только в приватных чатах с ботом
- При ошибках удаления функциональность не страдает, только остается визуальный след

## Совместимость

- ✅ Работает с существующими командами `/start`, `/stop`, `/settings`
- ✅ Совместимо с функцией очистки диалога при `/stop`
- ✅ Работает со всеми этапами регистрации и настройки
- ✅ Поддерживает обратную связь и изменение настроек 