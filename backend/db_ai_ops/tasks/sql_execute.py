"""
SQL执行任务
"""
import re
import time
import random
from datetime import datetime
from celery import shared_task
from ..models import db, SqlOrder, SqlOrderStatus, Backup, BackupStatus


@shared_task(bind=True, max_retries=3)
def execute_sql_order_task(self, order_id):
    """执行SQL工单"""
    print(f"[SQL Execute] Starting execute for order {order_id}")

    order = SqlOrder.query.get(order_id)
    if not order:
        print(f"[SQL Execute] Order {order_id} not found")
        return

    try:
        # 模拟执行SQL（实际应连接数据库执行）
        start_time = time.time()

        # 模拟执行时间
        time.sleep(random.uniform(0.5, 2.0))

        # 模拟结果
        execution_time = time.time() - start_time
        affected_rows = random.randint(0, 1000) if order.sql_type in ['UPDATE', 'DELETE', 'INSERT'] else 0

        # 生成回滚SQL（简单模拟）
        rollback_sql = generate_rollback_sql(order.sql_content, order.sql_type)

        # 更新工单状态
        order.status = SqlOrderStatus.EXECUTED
        order.execution_time = execution_time
        order.affected_rows = affected_rows
        order.rollback_sql = rollback_sql
        order.executed_at = datetime.utcnow()

        db.session.commit()

        print(f"[SQL Execute] Order {order_id} executed successfully, affected {affected_rows} rows")

        return {'success': True, 'affected_rows': affected_rows}

    except Exception as e:
        print(f"[SQL Execute] Order {order_id} failed: {e}")

        order.status = SqlOrderStatus.FAILED
        order.error_message = str(e)
        db.session.commit()

        raise self.retry(exc=e, countdown=60)


def generate_rollback_sql(sql, sql_type):
    """生成回滚SQL（简化版本）"""
    if sql_type == 'INSERT':
        # INSERT -> DELETE
        # 解析 INSERT 语句，提取表名和值
        match = re.search(r'INSERT\s+INTO\s+(\w+)', sql, re.IGNORECASE)
        if match:
            table = match.group(1)
            # 简单生成，实际需要解析 VALUES
            return f"-- 无法自动生成回滚SQL，请手动处理\n-- Original: {sql[:200]}"
        return None

    elif sql_type == 'UPDATE':
        # UPDATE -> 需要记录原值才能回滚
        return "-- UPDATE 操作需要手动备份数据后回滚"

    elif sql_type == 'DELETE':
        # DELETE -> INSERT（需要备份数据）
        return "-- DELETE 操作需要在执行前备份数据"

    return "-- 无需回滚"