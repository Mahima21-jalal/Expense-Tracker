import os
import csv
import datetime as dt
from dataclasses import dataclass

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

import mysql.connector as mysql
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pandas as pd

# ---------------------- MySQL CONFIG ----------------------
MYSQL_HOST = "localhost"
MYSQL_USER = "root"
MYSQL_PASSWORD = "Mahima@123"  
DB_NAME = "expense_db"
TABLE_NAME = "expenses"

# ---------------------- IMAGE PATHS (from your folder) -----------------------
BASE_IMG = r"D:\Expence Tracker Project\CollegeImages"
IMAGES = {
    "banner": os.path.join(BASE_IMG, "backgroundimg.jpg"),
    "dashboard_bg": os.path.join(BASE_IMG, "dashbg5.jpg"),
    "btn_add": os.path.join(BASE_IMG, "grop1.jpg"),
    "btn_view": os.path.join(BASE_IMG, "grop2.jpg"),
    "btn_reports": os.path.join(BASE_IMG, "viewdown.jpg"),
    "btn_summary": os.path.join(BASE_IMG, "viewnotices.jpg"),
    "window_bg": os.path.join(BASE_IMG, "loginbg.jpg")
}

DEFAULT_CATEGORIES = [
    "Food", "Travel", "Groceries", "Rent", "Utilities", "Shopping",
    "Health", "Education", "Entertainment", "Bills", "Other"
]

@dataclass
class Expense:
    date: dt.date
    category: str
    amount: float
    note: str

def get_connection(db: str | None = None):
    kwargs = dict(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD)
    if db:
        kwargs["database"] = db
    return mysql.connect(**kwargs)

def init_db():
    try:
        con = get_connection()
        cur = con.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cur.close(); con.close()
    except mysql.Error as e:
        raise

    ddl = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATE NOT NULL,
        category VARCHAR(64) NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        note VARCHAR(255) DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB;
    """
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(ddl)
    con.commit()
    cur.close(); con.close()

def insert_expense(exp: Expense):
    sql = f"INSERT INTO {TABLE_NAME} (date, category, amount, note) VALUES (%s, %s, %s, %s)"
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, (exp.date.isoformat(), exp.category, exp.amount, exp.note))
    con.commit()
    rid = cur.lastrowid
    cur.close(); con.close()
    return rid

def update_expense(row_id: int, exp: Expense):
    sql = f"UPDATE {TABLE_NAME} SET date=%s, category=%s, amount=%s, note=%s WHERE id=%s"
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, (exp.date.isoformat(), exp.category, exp.amount, exp.note, row_id))
    con.commit()
    cur.close(); con.close()

def delete_expense(row_id: int):
    sql = f"DELETE FROM {TABLE_NAME} WHERE id=%s"
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, (row_id,))
    con.commit()
    cur.close(); con.close()

def fetch_expenses(date_from: dt.date | None = None,
                   date_to: dt.date | None = None,
                   category: str | None = None,
                   text: str | None = None):
    where, params = [], []
    if date_from:
        where.append("date >= %s"); params.append(date_from.isoformat())
    if date_to:
        where.append("date <= %s"); params.append(date_to.isoformat())
    if category and category != "All":
        where.append("category = %s"); params.append(category)
    if text:
        where.append("(note LIKE %s OR category LIKE %s)"); params += [f"%{text}%", f"%{text}%"]

    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"SELECT id, date, category, amount, note FROM {TABLE_NAME}{where_sql} ORDER BY date DESC, id DESC"

    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, tuple(params))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows

def monthly_summary_year(year: int):
    sql = f"""
        SELECT MONTH(date) AS m, category, SUM(amount) AS total
        FROM {TABLE_NAME}
        WHERE YEAR(date) = %s
        GROUP BY m, category
        ORDER BY m, category;
    """
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, (year,))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows

def monthly_summary_one_month(year: int, month: int):
    sql = f"""
        SELECT category, SUM(amount) AS total
        FROM {TABLE_NAME}
        WHERE YEAR(date)=%s AND MONTH(date)=%s
        GROUP BY category ORDER BY total DESC;
    """
    con = get_connection(DB_NAME)
    cur = con.cursor()
    cur.execute(sql, (year, month))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows

class ImgStore:
    def __init__(self): self._store = {}
    def load(self, key, path, size=None):
        if not os.path.exists(path):
            # fallback to empty transparent image to avoid crash
            img = Image.new("RGBA", size or (200, 100), (240,240,240,255))
            p = ImageTk.PhotoImage(img)
            self._store[key] = p
            return p
        img = Image.open(path)
        if size: img = img.resize(size, Image.LANCZOS)
        p = ImageTk.PhotoImage(img)
        self._store[key] = p
        return p

# ---------------------- MAIN APP ------------------------
class Dashboard(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title("Expense Tracker – Dashboard")
        master.geometry("1366x768")
        master.minsize(1100, 650)
        self.pack(fill=tk.BOTH, expand=True)

        style = ttk.Style()
        try: style.theme_use("clam")
        except: pass
        style.configure("TButton", padding=6, font=("Segoe UI", 11, "bold"))

        self.imgs = ImgStore()

        # Banner (top)
        banner = self.imgs.load("banner", IMAGES["banner"], (1530, 150))
        tk.Label(master, image=banner).place(x=0, y=0, width=1530, height=150)

        # Background
        bg = self.imgs.load("dashboard_bg", IMAGES["dashboard_bg"], (1366, 768))
        self.bgimg = tk.Label(master, image=bg)
        self.bgimg.place(x=0, y=130, width=1366, height=600)

        # Title strip
        tk.Label(self.bgimg, text="EXPENSE TRACKER",
                 font=("Times New Roman", 28, "bold"),
                 bg="white", fg="red").place(x=0, y=0, width=1366, height=40)

        # Build buttons
        self._build_buttons()

    def _build_buttons(self):
        # Add Expense
        img_add = self.imgs.load("btn_add", IMAGES["btn_add"], (270, 200))
        tk.Button(self.bgimg, image=img_add, cursor="hand2",
                  command=self.open_add).place(x=150, y=190, width=250, height=160)
        tk.Button(self.bgimg, text="ADD EXPENSE", font=("times new roman", 15, "bold"),
                  bg="darkblue", fg="white", command=self.open_add).place(x=150, y=350, width=253, height=40)

        # View/Manage
        img_view = self.imgs.load("btn_view", IMAGES["btn_view"], (270, 200))
        tk.Button(self.bgimg, image=img_view, cursor="hand2",
                  command=self.open_view).place(x=550, y=80, width=250, height=160)
        tk.Button(self.bgimg, text="VIEW / MANAGE", font=("times new roman", 15, "bold"),
                  bg="darkblue", fg="white", command=self.open_view).place(x=550, y=220, width=253, height=40)

        # Reports
        img_rep = self.imgs.load("btn_reports", IMAGES["btn_reports"], (270, 200))
        tk.Button(self.bgimg, image=img_rep, cursor="hand2",
                  command=self.open_reports).place(x=550, y=350, width=250, height=160)
        tk.Button(self.bgimg, text="REPORTS", font=("times new roman", 15, "bold"),
                  bg="darkblue", fg="white", command=self.open_reports).place(x=550, y=480, width=253, height=40)

        # Monthly Summary
        img_sum = self.imgs.load("btn_summary", IMAGES["btn_summary"], (270, 200))
        tk.Button(self.bgimg, image=img_sum, cursor="hand2",
                  command=self.open_monthly_summary).place(x=950, y=190, width=250, height=160)
        tk.Button(self.bgimg, text="MONTHLY SUMMARY", font=("times new roman", 15, "bold"),
                  bg="darkblue", fg="white", command=self.open_monthly_summary).place(x=950, y=350, width=253, height=40)

    # ---------------- Add Expense ----------------
    def open_add(self):
        win = tk.Toplevel(self)
        win.title("ADD EXPENCE")
        win.geometry("900x600")
        self._window_bg(win)

        form = ttk.LabelFrame(win, text="ADD EXPENCE", padding=16)
        form.place(x=40, y=80, width=820, height=200)

        ttk.Label(form, text="Date (YYYY-MM-DD)").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
        var_date = tk.StringVar(value=dt.date.today().isoformat())
        ttk.Entry(form, textvariable=var_date, width=18).grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(form, text="Category").grid(row=0, column=2, padx=8, pady=8, sticky=tk.W)
        var_cat = tk.StringVar(value=DEFAULT_CATEGORIES[0])
        ttk.Combobox(form, textvariable=var_cat, values=DEFAULT_CATEGORIES,
                     state="readonly", width=20).grid(row=0, column=3, padx=8, pady=8)

        ttk.Label(form, text="Amount").grid(row=1, column=0, padx=8, pady=8, sticky=tk.W)
        var_amt = tk.StringVar()
        ttk.Entry(form, textvariable=var_amt, width=18).grid(row=1, column=1, padx=8, pady=8)

        ttk.Label(form, text="Note").grid(row=1, column=2, padx=8, pady=8, sticky=tk.W)
        txt_note = ttk.Entry(form, width=32)
        txt_note.grid(row=1, column=3, padx=8, pady=8)

        def do_save():
            try:
                d = dt.date.fromisoformat(var_date.get().strip())
            except Exception:
                messagebox.showwarning("Invalid", "Invalid date. Use YYYY-MM-DD."); return
            try:
                amount = float(var_amt.get().strip()); assert amount > 0
            except Exception:
                messagebox.showwarning("Invalid", "Amount must be a positive number."); return
            exp = Expense(d, var_cat.get().strip(), amount, txt_note.get().strip())
            try:
                insert_expense(exp)
                messagebox.showinfo("Saved", "Expense saved.")
                var_amt.set(""); txt_note.delete(0, tk.END)
            except mysql.Error as e:
                messagebox.showerror("MySQL Error", str(e))

        ttk.Button(form, text="Save Expense", command=do_save).grid(row=2, column=0, padx=8, pady=10)
        ttk.Button(form, text="Close", command=win.destroy).grid(row=2, column=1, padx=8, pady=10)

    # ---------------- View / Manage ----------------
    def open_view(self):
        win = tk.Toplevel(self)
        win.title("View / Manage")
        win.geometry("1100x640")
        self._window_bg(win)

        filters = ttk.LabelFrame(win, text="Filters", padding=10)
        filters.place(x=20, y=60, width=1060, height=90)

        ttk.Label(filters, text="From (YYYY-MM-DD)").grid(row=0, column=0, padx=6, pady=6)
        var_from = tk.StringVar(); ttk.Entry(filters, textvariable=var_from, width=16).grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(filters, text="To (YYYY-MM-DD)").grid(row=0, column=2, padx=6, pady=6)
        var_to = tk.StringVar(); ttk.Entry(filters, textvariable=var_to, width=16).grid(row=0, column=3, padx=6, pady=6)

        ttk.Label(filters, text="Category").grid(row=0, column=4, padx=6, pady=6)
        var_cat = tk.StringVar(value="All")
        ttk.Combobox(filters, textvariable=var_cat, values=["All"] + DEFAULT_CATEGORIES,
                     state="readonly", width=18).grid(row=0, column=5, padx=6, pady=6)

        ttk.Label(filters, text="Search").grid(row=0, column=6, padx=6, pady=6)
        var_txt = tk.StringVar(); ttk.Entry(filters, textvariable=var_txt, width=18).grid(row=0, column=7, padx=6, pady=6)

        columns = ("id", "date", "category", "amount", "note")
        tree = ttk.Treeview(win, columns=columns, show="headings", height=16)
        for c, w in zip(columns, (60, 110, 160, 120, 540)):
            tree.heading(c, text=c.title()); tree.column(c, width=w, anchor=tk.W)
        vsb = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.place(x=20, y=160, width=1020, height=380)
        vsb.place(x=1040, y=160, height=380)

        def parse_date_or_none(s):
            s = s.strip()
            if not s: return None
            try: return dt.date.fromisoformat(s)
            except ValueError:
                messagebox.showwarning("Invalid", f"Invalid date: {s}"); return None

        def refresh():
            for r in tree.get_children(): tree.delete(r)
            df = parse_date_or_none(var_from.get()); dt_ = parse_date_or_none(var_to.get())
            rows = fetch_expenses(df, dt_, var_cat.get(), var_txt.get().strip())
            for row in rows: tree.insert("", tk.END, values=row)

        def clear_filters():
            var_from.set(""); var_to.set(""); var_cat.set("All"); var_txt.set(""); refresh()

        ttk.Button(filters, text="Apply", command=refresh).grid(row=0, column=8, padx=6)
        ttk.Button(filters, text="Clear", command=clear_filters).grid(row=0, column=9, padx=6)

        def selected_id():
            sel = tree.selection()
            if not sel:
                messagebox.showinfo("Select", "Please select a row."); return None
            return int(tree.item(sel[0], "values")[0])

        def do_edit():
            rid = selected_id(); 
            if rid is None: return
            sel = tree.selection()[0]
            _, date_str, category, amount, note = tree.item(sel, "values")
            edit = tk.Toplevel(win); edit.title(f"Edit #{rid}"); edit.geometry("420x260")
            ttk.Label(edit, text="Date (YYYY-MM-DD)").grid(row=0, column=0, padx=8, pady=8, sticky=tk.W)
            var_d = tk.StringVar(value=date_str); ttk.Entry(edit, textvariable=var_d).grid(row=0, column=1, padx=8, pady=8)
            ttk.Label(edit, text="Category").grid(row=1, column=0, padx=8, pady=8, sticky=tk.W)
            var_c = tk.StringVar(value=category)
            ttk.Combobox(edit, textvariable=var_c, values=DEFAULT_CATEGORIES, state="readonly").grid(row=1, column=1, padx=8, pady=8)
            ttk.Label(edit, text="Amount").grid(row=2, column=0, padx=8, pady=8, sticky=tk.W)
            var_a = tk.StringVar(value=str(amount)); ttk.Entry(edit, textvariable=var_a).grid(row=2, column=1, padx=8, pady=8)
            ttk.Label(edit, text="Note").grid(row=3, column=0, padx=8, pady=8, sticky=tk.W)
            var_n = tk.StringVar(value=note); ttk.Entry(edit, textvariable=var_n, width=32).grid(row=3, column=1, padx=8, pady=8)

            def save_edit():
                try:
                    d = dt.date.fromisoformat(var_d.get().strip())
                    a = float(var_a.get().strip()); assert a > 0
                except Exception:
                    messagebox.showwarning("Invalid", "Check date and amount."); return
                exp = Expense(d, var_c.get().strip(), a, var_n.get().strip())
                try:
                    update_expense(rid, exp); messagebox.showinfo("Updated", "Expense updated.")
                except mysql.Error as e:
                    messagebox.showerror("MySQL Error", str(e))
                edit.destroy(); refresh()

            ttk.Button(edit, text="Save", command=save_edit).grid(row=4, column=0, padx=8, pady=10)
            ttk.Button(edit, text="Cancel", command=edit.destroy).grid(row=4, column=1, padx=8, pady=10)

        def do_delete():
            rid = selected_id()
            if rid is None: return
            if not messagebox.askyesno("Confirm", "Delete selected expense?"): return
            try:
                delete_expense(rid); refresh(); messagebox.showinfo("Deleted", "Expense deleted.")
            except mysql.Error as e:
                messagebox.showerror("MySQL Error", str(e))

        def export_csv():
            path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV Files","*.csv")],
                                                initialfile="expenses.csv")
            if not path: return
            rows = fetch_expenses(parse_date_or_none(var_from.get()),
                                parse_date_or_none(var_to.get()),
                                var_cat.get(), var_txt.get().strip())
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f); w.writerow(["ID","Date","Category","Amount","Note"])
                for r in rows: w.writerow(r)
            messagebox.showinfo("Exported", f"Saved: {path}")

        ttk.Button(win, text="Edit Selected", command=do_edit).place(x=20, y=560)
        ttk.Button(win, text="Delete Selected", command=do_delete).place(x=160, y=560)
        ttk.Button(win, text="Export CSV", command=export_csv).place(x=320, y=560)
        ttk.Button(win, text="Refresh", command=refresh).place(x=460, y=560)
        refresh()

    # ---------------- Reports ---------
    def open_reports(self):
        win = tk.Toplevel(self)
        win.title("Reports")
        win.geometry("1100x680")
        self._window_bg(win)

        top = ttk.Frame(win); top.place(x=20, y=60)
        ttk.Label(top, text="Year").pack(side=tk.LEFT)
        var_year = tk.StringVar(value=str(dt.date.today().year))
        ttk.Entry(top, textvariable=var_year, width=8).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Generate", command=lambda: render()).pack(side=tk.LEFT, padx=6)

        table = ttk.Treeview(win, columns=("month","category","total"), show="headings", height=10)
        for c, w in zip(("month","category","total"), (100, 240, 160)):
            table.heading(c, text=c.title()); table.column(c, width=w, anchor=tk.W)
        table.place(x=20, y=110, width=1060, height=240)

        bar_frame = ttk.LabelFrame(win, text="Monthly Totals (Bar)")
        bar_frame.place(x=20, y=360, width=520, height=280)
        pie_frame = ttk.LabelFrame(win, text="Category Share (Pie)")
        pie_frame.place(x=560, y=360, width=520, height=280)

        def render():
            for r in table.get_children(): table.delete(r)
            for c in bar_frame.winfo_children(): c.destroy()
            for c in pie_frame.winfo_children(): c.destroy()
            try:
                y = int(var_year.get()); assert 2000 <= y <= 3000
            except Exception:
                messagebox.showwarning("Invalid", "Enter a valid year (e.g., 2025)"); return

            rows = monthly_summary_year(y)
            if not rows:
                messagebox.showinfo("No Data", f"No expenses found for {y}."); return

            for m, cat, tot in rows:
                table.insert("", tk.END, values=(m, cat, float(tot)))

            df = pd.DataFrame(rows, columns=["month","category","total"]).astype({"month": int, "total": float})
            monthly_totals = df.groupby("month")["total"].sum().reindex(range(1,13), fill_value=0.0)

            f1 = Figure(figsize=(5.2, 2.8), dpi=100); ax1 = f1.add_subplot(111)
            ax1.bar(monthly_totals.index, monthly_totals.values)
            ax1.set_title(f"Monthly Totals - {y}"); ax1.set_xlabel("Month"); ax1.set_ylabel("Amount")
            ax1.set_xticks(range(1,13))
            FigureCanvasTkAgg(f1, master=bar_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

            year_cats = df.groupby("category")["total"].sum().sort_values(ascending=False)
            f2 = Figure(figsize=(5.2, 2.8), dpi=100); ax2 = f2.add_subplot(111)
            ax2.pie(year_cats.values, labels=year_cats.index, autopct="%1.1f%%", startangle=120)
            ax2.set_title(f"Category Share - {y}")
            FigureCanvasTkAgg(f2, master=pie_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        render()

    # ---------------- Monthly Summary Dashboard ----------
    def open_monthly_summary(self):
        win = tk.Toplevel(self)
        win.title("Monthly Summary")
        win.geometry("1100x680")
        self._window_bg(win)

        controls = ttk.Frame(win)
        controls.place(x=20, y=60)

        this_year = dt.date.today().year
        this_month = dt.date.today().month

        ttk.Label(controls, text="Year").grid(row=0, column=0, padx=6, pady=6)
        var_y = tk.StringVar(value=str(this_year))
        ttk.Entry(controls, textvariable=var_y, width=8).grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(controls, text="Month").grid(row=0, column=2, padx=6, pady=6)
        var_m = tk.StringVar(value=str(this_month))
        ttk.Combobox(controls, textvariable=var_m, values=[str(i) for i in range(1,13)],
                     width=6, state="readonly").grid(row=0, column=3, padx=6, pady=6)

        ttk.Button(controls, text="Show", command=lambda: render()).grid(row=0, column=4, padx=8)

        year_table = ttk.Treeview(win, columns=("Month", "Total"), show="headings", height=10)
        year_table.heading("Month", text="Month"); year_table.column("Month", width=120, anchor=tk.W)
        year_table.heading("Total", text="Total Expense"); year_table.column("Total", width=160, anchor=tk.W)
        year_table.place(x=20, y=110, width=400, height=240)

        bar_frame = ttk.LabelFrame(win, text="Monthly Totals (Selected Year)")
        bar_frame.place(x=440, y=110, width=640, height=240)

        pie_frame = ttk.LabelFrame(win, text="Selected Month – Category Share")
        pie_frame.place(x=20, y=370, width=1060, height=280)

        def render():
            for c in bar_frame.winfo_children(): c.destroy()
            for c in pie_frame.winfo_children(): c.destroy()
            for r in year_table.get_children(): year_table.delete(r)

            try:
                y = int(var_y.get()); m = int(var_m.get())
                assert 2000 <= y <= 3000 and 1 <= m <= 12
            except Exception:
                messagebox.showwarning("Invalid", "Enter a valid year/month."); return

            rows_y = monthly_summary_year(y)
            df_y = pd.DataFrame(rows_y, columns=["month","category","total"]).astype({"month": int, "total": float}) if rows_y else pd.DataFrame(columns=["month","category","total"])
            monthly_totals = df_y.groupby("month")["total"].sum().reindex(range(1,13), fill_value=0.0)

            for mi, val in monthly_totals.items():
                year_table.insert("", tk.END, values=(mi, float(val)))

            f1 = Figure(figsize=(6.0, 2.4), dpi=100); ax1 = f1.add_subplot(111)
            ax1.bar(monthly_totals.index, monthly_totals.values)
            ax1.set_title(f"Monthly Totals - {y}"); ax1.set_xlabel("Month"); ax1.set_ylabel("Amount")
            ax1.set_xticks(range(1,13))
            FigureCanvasTkAgg(f1, master=bar_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

            rows_m = monthly_summary_one_month(y, m)
            if not rows_m:
                tk.Label(pie_frame, text="No data for selected month.", font=("Segoe UI", 11)).pack(pady=30)
                return
            df_m = pd.DataFrame(rows_m, columns=["category","total"]).astype({"total": float})
            f2 = Figure(figsize=(9.8, 2.6), dpi=100); ax2 = f2.add_subplot(111)
            ax2.pie(df_m["total"].values, labels=df_m["category"].values, autopct="%1.1f%%", startangle=120)
            ax2.set_title(f"Category Share - {y}-{m:02d}")
            FigureCanvasTkAgg(f2, master=pie_frame).get_tk_widget().pack(fill=tk.BOTH, expand=True)

        render()

    # ---------------- Window Background helper ----------
    def _window_bg(self, win: tk.Toplevel):
        try:
            bgimg = Image.open(IMAGES["window_bg"]).resize((1100, 680), Image.LANCZOS)
            photo = ImageTk.PhotoImage(bgimg)
            lbl = tk.Label(win, image=photo)
            lbl.image = photo
            lbl.place(x=0, y=0, width=1100, height=680)
        except Exception:
            pass
        tk.Label(win, text=win.title(), font=("Times New Roman", 20, "bold"),
                 bg="white", fg="red").place(x=0, y=0, relwidth=1.0, height=40)

# ---------------------- MAIN ----------------------------
if __name__ == "__main__":
    try:
        init_db()
    except mysql.Error as e:
        messagebox.showerror("MySQL", f"Database init failed: {e}\n\nTip: Check MYSQL_PASSWORD.")
        raise

    root = tk.Tk()
    app = Dashboard(root)
    root.mainloop()
