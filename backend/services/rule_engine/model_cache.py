# -*- coding: utf-8 -*-
"""模型缓存 - 避免重复加载模型。

规则图执行时，同一模型可能在多个节点或多个执行批次中被重复加载。
ModelCache 提供 LRU 淘汰策略，减少 I/O 和初始化开销。
"""
import logging
import time
from collections import OrderedDict
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class ModelCache:
    """模型缓存 - LRU 淘汰策略。

    缓存已加载的模型实例，超过 max_size 时淘汰最久未访问的。
    支持 TTL 过期和主动清除。

    使用示例:
        cache = ModelCache.get_instance()
        model = cache.get_or_load("model_5", lambda: load_model("/path/to/model.pt"))
    """

    _instance: Optional["ModelCache"] = None

    def __init__(self, max_size: int = 5, ttl: int = 600):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl

    @classmethod
    def get_instance(cls, max_size: int = 5, ttl: int = 600) -> "ModelCache":
        """获取全局单例。"""
        if cls._instance is None:
            cls._instance = cls(max_size=max_size, ttl=ttl)
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """获取缓存的模型，未命中或已过期返回 None。

        命中时将该条目移到末尾（表示最近使用）。
        """
        if key not in self._cache:
            return None

        model, timestamp = self._cache[key]
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            logger.debug("模型缓存过期: %s", key)
            return None

        self._cache.move_to_end(key)
        logger.debug("模型缓存命中: %s", key)
        return model

    def put(self, key: str, model: Any) -> None:
        """放入模型，超出容量时淘汰最久未使用的。"""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug("模型缓存淘汰: %s", evicted_key)

        self._cache[key] = (model, time.time())

    def get_or_load(self, key: str, loader: Callable[[], Any]) -> Any:
        """缓存中获取，未命中则调用 loader 加载并缓存。"""
        model = self.get(key)
        if model is not None:
            return model

        logger.info("模型缓存未命中，加载: %s", key)
        model = loader()
        self.put(key, model)
        return model

    def remove(self, key: str) -> None:
        """主动移除缓存的模型。"""
        self._cache.pop(key, None)
        logger.debug("模型缓存移除: %s", key)

    def clear(self) -> None:
        """清空所有缓存。"""
        self._cache.clear()
        logger.info("模型缓存已清空")

    def keys(self) -> list[str]:
        """返回当前缓存的 key 列表。"""
        return list(self._cache.keys())

    @property
    def size(self) -> int:
        return len(self._cache)
