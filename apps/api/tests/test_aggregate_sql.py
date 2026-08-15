from metaforge_api.domain.metadata import AggregateOp
from metaforge_api.infrastructure.repository import build_aggregate_update_sql


def test_sum_aggregate_sql_is_scoped_to_parent_and_excludes_deleted():
    sql = build_aggregate_update_sql("orders", "subtotal", "order_items", "order_id", "line_total", AggregateOp.SUM)
    assert sql == (
        "UPDATE biz_orders SET subtotal = ("
        "SELECT COALESCE(SUM(line_total), 0) FROM biz_order_items "
        "WHERE order_id = biz_orders.id AND deleted_at IS NULL"
        ") WHERE id = :parent_id"
    )


def test_count_aggregate_uses_count_star():
    sql = build_aggregate_update_sql("orders", "line_count", "order_items", "order_id", "id", AggregateOp.COUNT)
    assert "COALESCE(COUNT(*), 0)" in sql


def test_filtered_rollup_adds_bound_filter_clause():
    sql = build_aggregate_update_sql(
        "invoices", "open_balance", "invoice_lines", "invoice_id", "amount", AggregateOp.SUM,
        filter_field="status",
    )
    assert sql == (
        "UPDATE biz_invoices SET open_balance = ("
        "SELECT COALESCE(SUM(amount), 0) FROM biz_invoice_lines "
        "WHERE invoice_id = biz_invoices.id AND deleted_at IS NULL AND status = :filter_value"
        ") WHERE id = :parent_id"
    )


def test_unfiltered_rollup_has_no_filter_clause():
    sql = build_aggregate_update_sql("orders", "subtotal", "order_items", "order_id", "line_total", AggregateOp.SUM)
    assert "filter_value" not in sql
