# routes/inventory.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from services.inventory_service import get_inventory_item, get_all_consumables, add_consumable, update_consumable, delete_consumable

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    if request.method == "POST":
        if current_user.role not in ['manager', 'admin']:
            flash("Permission denied.")
            return redirect(url_for('inventory.inventory'))
        item_id = request.form.get("item_id")
        item = get_inventory_item(item_id)
        if not item:
            flash("Item not found.")
            return redirect(url_for('inventory.inventory'))
        if "update_quantity" in request.form:
            additional_quantity = int(request.form.get("additional_quantity", 0))
            if additional_quantity > 0:
                new_quantity = item["quantity"] + additional_quantity
                update_consumable(
                    item_id, item["name"], item["location"], new_quantity,
                    item["supplier"], item["serial_numbers"], item["unit"],
                    item["reorder_threshold"], current_user.id
                )
                flash(f"Added {additional_quantity} to {item['name']}.")
        elif "reduce_quantity" in request.form:
            reduce_quantity = int(request.form.get("reduce_quantity", 0))
            if reduce_quantity > 0:
                new_quantity = max(0, item["quantity"] - reduce_quantity)
                update_consumable(
                    item_id, item["name"], item["location"], new_quantity,
                    item["supplier"], item["serial_numbers"], item["unit"],
                    item["reorder_threshold"], current_user.id
                )
                flash(f"Removed {reduce_quantity} from {item['name']}.")
    items = get_all_consumables()
    return render_template("inventory.html", inventory=items, can_edit=current_user.role in ['manager', 'admin'])

@inventory_bp.route("/list")
@login_required
def index():
    items = get_all_consumables()
    return render_template("inventory.html", inventory=items, can_edit=current_user.role in ['manager', 'admin'])

@inventory_bp.route('/inventory/<int:item_id>', methods=['GET'])
@login_required
def inventory_detail(item_id):
    item = get_inventory_item(item_id)
    if not item:
        flash('Item not found.')
        return redirect(url_for('inventory.inventory'))
    return render_template('inventory_detail.html', item=item, can_edit=current_user.role in ['manager', 'admin'])

@inventory_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_inventory():
    if current_user.role not in ['manager', 'admin']:
        flash("Permission denied.")
        return redirect(url_for('inventory.inventory'))
    if request.method == "POST":
        try:
            name = request.form.get("name")
            location = request.form.get("location")
            quantity = int(request.form.get("quantity"))
            supplier = request.form.get("supplier")
            serial_numbers = request.form.get("serial_numbers")
            unit = request.form.get("unit")
            reorder_threshold = int(request.form.get("reorder_threshold", 0))
            add_consumable(name, location, quantity, supplier, serial_numbers, unit, reorder_threshold, current_user.id)
            flash("Inventory item added.")
            return redirect(url_for("inventory.inventory"))
        except ValueError as e:
            flash(f"Error adding item: {str(e)}")
    return render_template("add_inventory.html")

@inventory_bp.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit_inventory(item_id):
    if current_user.role not in ['manager', 'admin']:
        flash("Permission denied.")
        return redirect(url_for('inventory.inventory'))
    item = get_inventory_item(item_id)
    if not item:
        flash("Item not found.")
        return redirect(url_for("inventory.inventory"))
    if request.method == "POST":
        try:
            name = request.form.get("name")
            location = request.form.get("location")
            quantity = int(request.form.get("quantity"))
            supplier = request.form.get("supplier")
            serial_numbers = request.form.get("serial_numbers")
            unit = request.form.get("unit")
            reorder_threshold = int(request.form.get("reorder_threshold", 0))
            update_consumable(item_id, name, location, quantity, supplier, serial_numbers, unit, reorder_threshold, current_user.id)
            flash("Inventory item updated.")
            return redirect(url_for("inventory.inventory"))
        except ValueError as e:
            flash(f"Error updating item: {str(e)}")
    return render_template("edit_inventory.html", item=item)

@inventory_bp.route("/delete/<int:item_id>", methods=["POST"])
@login_required
def delete_inventory(item_id):
    if current_user.role not in ['manager', 'admin']:
        flash("Permission denied.")
        return redirect(url_for('inventory.inventory'))
    delete_consumable(item_id, current_user.id)
    flash("Inventory item deleted.")
    return redirect(url_for("inventory.inventory"))