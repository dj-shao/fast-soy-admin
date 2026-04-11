from fastapi import APIRouter, Depends

from app.core.dependency import AuthControl

router = APIRouter(tags=["Health"])


@router.get("/health", summary="健康检测")
async def health_check():
    """健康检测接口，用于 Docker/K8s 探针"""
    return {"status": "ok"}


class OrderService:
    """模拟业务服务层"""

    def __init__(self, user_id: int):
        self.user_id = user_id

    def create_order(self, items: list[dict]) -> dict:
        total = self._calculate_total(items)
        return self._submit_order(self.user_id, items, total)

    def _calculate_total(self, items: list[dict]) -> float:
        total = 0.0
        for item in items:
            price = item["price"]
            quantity = item["quantity"]
            discount = self._get_discount(item["product_id"])
            total += price * quantity * discount
        return round(total, 2)

    @staticmethod
    def _get_discount(product_id: int) -> float:
        discounts = {1001: 0.9, 1002: 0.85, 1003: 0.0}
        rate = discounts.get(product_id, 1.0)
        # Bug：商品 1003 的折扣为 0.0，下方除法将触发除零错误
        return 1.0 / rate

    @staticmethod
    def _submit_order(user_id: int, items: list[dict], total: float) -> dict:
        return {"user_id": user_id, "items": items, "total": total, "status": "created"}


def process_user_request(user_id: int) -> dict:
    """模拟控制器层调用"""
    service = OrderService(user_id)
    cart_items = [
        {"product_id": 1001, "name": "键盘", "price": 299.0, "quantity": 1},
        {"product_id": 1002, "name": "鼠标", "price": 149.0, "quantity": 2},
        {"product_id": 1003, "name": "显示器", "price": 2999.0, "quantity": 1},
    ]
    return service.create_order(cart_items)


@router.get("/api/v1/test-error", summary="测试错误", tags=["Test"], dependencies=[Depends(AuthControl.is_authed)])
async def test_error():
    """测试错误接口（需鉴权），用于验证异常捕获和 Radar 监控"""
    return process_user_request(user_id=42)
