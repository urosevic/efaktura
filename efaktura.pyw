# Copyright 2023 TechWebUX doo

import os
import re
import json
import base64
import requests
import tkinter as tk
from tkinter import Frame, Label, Button, messagebox
from tkinter.font import Font
from xml.etree import ElementTree as ET

# Постављамо глобалне променљиве
title = "еФактура: Нове примљене фактуре"
check_guide = "\n\nКонсултујте упутство за подешавање скрипта."
color_primary = "#0ca275"
color_primary_hover = "#01ce96"
have_processed_invoices = False

# Иницирамо графичку библиотеку
app = tk.Tk()

# Постављамо нове фонт објекте са предодређеним словоликом и величином
font = Font(family="Segoe UI", size=10)
font_h1 = Font(family="Segoe UI", size=16)

# Сакривамо главни прозор
app.withdraw()

# Постављамо особине прозора
app.title(title)
app.minsize(470, 230)  # шрина, висина 388
app.configure(background="white")

# Постављамо иконицу главног прозора
icon_path = os.path.join(os.path.dirname(__file__), 'efaktura.ico')
if os.path.isfile(icon_path):
    app.iconbitmap(icon_path)

# Направи директоријум ако недостаје
efakture_dir = os.path.join(os.path.dirname(__file__), "efakture")
if (os.path.isdir(efakture_dir) != True):
    os.makedirs(efakture_dir)

# Функција за учитавање АПИ кључа
def get_api_key():
    # Учитавамо датотека са подешавањима `config.json` ако постоји
    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.isfile(config_file):
        with open(config_file, "r") as c:
            config = json.load(c)
            # Проверавамо да ли датотека са подешавањима садржи АПИ кључ
            ApiKey = config.get('ApiKey')
            if ApiKey is not None:
                # Ако кључ постоји, проверавамо да ли је исти у исправном облику
                pattern = re.compile(
                    "^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$")
                if pattern.match(ApiKey):
                    return ApiKey
                else:
                    messagebox.showerror(
                        title, f"АПИ кључ {ApiKey}\nније у исправном облику! {check_guide}")
            else:
                messagebox.showerror(
                    title, f"У датотеци са подешавањима нисмо пронашли АПИ кључ. {check_guide}")
    else:
        # Јављамо грешку ако датотека са подешавањима не постоји
        messagebox.showerror(
            title, f"Датотека са подешавањима {config_file} не постоји! {check_guide}")

    # Враћамо подразумевану вредност АПИ кључа
    return None

# Функција за добављање списка нових улазних фактура
def get_new_invoices(api_key):
    # Преузимамо списак улазних фактура које су означене као `Ново`
    headers = {'ApiKey': api_key}
    endpoint = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/ids?status=New"
    try:
        response = requests.post(endpoint, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            # Редни бројеви нових улазних фактура се налазе у ЈСОН чвору `PurchaseInvoiceIds`
            json_obj = response.json()
            invoice_ids = json_obj.get('PurchaseInvoiceIds')
            # Ако није празан, враћамо списак нових улазних фактура
            if (type(invoice_ids) == list) and (len(invoice_ids) > 0):
                return invoice_ids
            else:
                messagebox.showinfo(title, "Нема нових улазних фактура.")
        else:
            messagebox.showerror(
                title, f"Догодила се грешка {response.status_code} приликом преузимања списка нових улазних фактура са портала еФактура.")
    except requests.exceptions.RequestException as e:
        # Јављамо ако постоји нека грешка у одговору од портала еФактура
        messagebox.showerror(title, "Догодила се грешка: " + str(e))
        # raise SystemExit(e)

    # Враћамо празан списак ако се догодила нека грешка
    return {}

# Функција за обраду и преузимање појединачне фактуре
def parse_invoice(api_key, invoice_id):
    # Преузимамо ИксМЛ запис за захтевану фактуру
    headers = {'ApiKey': api_key}
    endpoint = f"https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/xml?invoiceId={invoice_id}"
    xml_response = requests.get(endpoint, headers=headers)

    if xml_response.status_code == 200:
        target_file = os.path.join(os.path.dirname(
            __file__), "efakture", invoice_id)
        xml_content = xml_response.content
        # Чувањмо улазну фактуре у ИксМЛ датотеку
        with open(f"{target_file}.xml", "wb") as f:
            f.write(xml_content)

        xml = ET.fromstring(xml_response.content)

        namespace = {"cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
                     "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                     "env": "urn:eFaktura:MinFinrs:envelop:schema"}

        # Проналазимо Идентификатор документа
        document_id = xml.find(
            ".//env:DocumentId", namespaces={"env": "urn:eFaktura:MinFinrs:envelop:schema"})
        if document_id is not None:
            document_id = document_id.text
        else:
            document_id = "непознато"

        # Проналазимо број фактуре
        payment_invoice_id = xml.find(
            ".//cbc:ID", namespaces=namespace)
        if payment_invoice_id is not None:
            payment_invoice_id = payment_invoice_id.text
        else:
            payment_invoice_id = "непознато"

        # Проналазимо назив добављача
        supplier_name = xml.find(
            ".//cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name", namespaces=namespace)
        if supplier_name is not None:
            supplier_name = supplier_name.text
        else:
            # Покушамо и на другој локацији
            supplier_name = xml.find(
                ".//cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName", namespaces=namespace)
            if supplier_name is not None:
                supplier_name = supplier_name.text
            else:
                supplier_name = "непознато"

        # Проналазимо износ улазне фактуре
        amount = xml.find(
            ".//cac:LegalMonetaryTotal/cbc:PayableAmount", namespaces=namespace)
        if amount is not None:
            amount = amount.text
        else:
            amount = "непознато"

        # Проналазимо валуту улазне фактуре
        currency = xml.find(
            ".//cbc:DocumentCurrencyCode", namespaces=namespace)
        if currency is not None:
            currency = currency.text
        else:
            currency = "непознато"

        # Проналазимо датум промета улазне фактуре
        delivery_date = xml.find(
            ".//cbc:ActualDeliveryDate", namespaces=namespace)
        if delivery_date is not None:
            delivery_date = delivery_date.text
        else:
            delivery_date = "непознато"

        # Проналазимо датум доспећа улазне фактуре
        due_date = xml.find(
            ".//cbc:DueDate", namespaces=namespace)
        if due_date is not None:
            due_date = due_date.text
        else:
            due_date = "непознато"

        # ПОстављамо информациј о новој улазној фактури
        invoice_data = [
            ["Добављач:", supplier_name],
            ["Датум промета:", delivery_date],
            ["Датум доспећа:", due_date],
            ["Број документа:", payment_invoice_id],
            ["Износ:", f"{amount} {currency}"],
            ["еФ Редни број:", invoice_id],
            ["еФ Идентификатор:", document_id],
        ]

        # Декодирамо `base64` ниску из ИксМЛа
        pdf_base64 = xml.find(
            ".//env:DocumentPdf", namespaces={"env": "urn:eFaktura:MinFinrs:envelop:schema"})
        if pdf_base64 is not None:
            pdf_base64 = pdf_base64.text
            if pdf_base64 is not None:
                pdf_content = base64.b64decode(pdf_base64.encode())

                # Чувамо улазну фактуру у PDF
                with open(f"{target_file}.pdf", "wb") as f:
                    f.write(pdf_content)

        # Формирамо табелу са подацима о улазној фактури
        create_table(app, invoice_data, invoice_id)

        # Враћамо `invoice_data``
        return invoice_data

    else:
        messagebox.showerror(
            title, f"Догодила се грешка приликом преузимања података о еФактури под редним бројем {invoice_id}")
        return None

# Функција за креирање табеле са информацијама о фактури
def create_table(app, data, invoice_id):
    table_frame = Frame(app, padx=20, bg="white")
    table_frame.pack(expand=True, fill="both")

    i = 0
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            label = Label(table_frame, text=value, font=font,
                          bg="white", fg="black")
            if j % 2 == 0:
                label.config(width=20, anchor="e")
            else:
                label.config(width=40, anchor="w")
            label.grid(row=i, column=j, sticky="w")

    # Додајемо оквир за дугмад
    btns_frame = tk.Frame(table_frame, bg="white")
    btns_frame.grid(row=i+1, column=0, columnspan=2, sticky="ew")

    # Додајемо дугме за приказ локално сачуване ПДФ датотеке
    dugme_pdf = Button(btns_frame,
                   text="Види ПДФ",
                   fg="white",
                   bg=color_primary,
                   activebackground=color_primary_hover,
                   activeforeground="white",
                   font=font,
                   cursor="hand2",
                   padx=20,
                   pady=5,
                   relief="flat",
                   command=lambda: view_pdf(invoice_id)
                   )

    # Додавајемо дугме за отварање фактуре на порталу еФактура
    dugme = Button(btns_frame,
                   text="Уреди на порталу еФактура",
                   fg="white",
                   bg=color_primary,
                   activebackground=color_primary_hover,
                   activeforeground="white",
                   font=font,
                   cursor="hand2",
                   padx=20,
                   pady=5,
                   relief="flat",
                   command=lambda: open_url(None, invoice_id)
                   )

    # Повезујемо догаћаје са функцијама
    dugme.bind("<Enter>", change_bg_color_enter)
    dugme.bind("<Leave>", change_bg_color_leave)
    dugme_pdf.bind("<Enter>", change_bg_color_enter)
    dugme_pdf.bind("<Leave>", change_bg_color_leave)

    # Додајемо дугмад у оквир
    dugme.pack(padx=(20, 0), pady=(10, 20), anchor='e', side='right')
    dugme_pdf.pack(padx=0, pady=(10, 20), anchor='e', side='right')


# Функција која мења позадину дугмета када се курсор миша налази изнад њега
def change_bg_color_enter(event):
    event.widget.config(bg=color_primary_hover)

# Функција која мења позадину дугмета када се курсор миша склони ван њега
def change_bg_color_leave(event):
    event.widget.config(bg=color_primary)

# Функција која отвара хипер везу на порталу еФактура
def open_url(event, id):
    import webbrowser
    webbrowser.open_new(f"https://efaktura.mfin.gov.rs/purchases/edit/{id}")

# Функција која отвара ПДФ датотеку
def view_pdf(invoice_id):
    import subprocess
    file = os.path.join(os.path.dirname(__file__), "efakture", f"{invoice_id}.pdf")
    subprocess.Popen([file], shell=True)


# Добављамо АПИ кључ
api_key = get_api_key()
if api_key is not None:
    invoice_ids = get_new_invoices(api_key)
    # Обрађујемо сваку појединачну фактуру
    if len(invoice_ids) > 0:
        for invoice_id in invoice_ids:
            parsed = parse_invoice(api_key, invoice_id)
            if parsed is not None:
                have_processed_invoices = True

        # Ажурирамо димензије прозора у управнику геометријом
        app.update_idletasks()
        # Задајемо нове координате за центрирање прозора на екрану
        x = (app.winfo_screenwidth() - app.winfo_width()) / 2
        y = (app.winfo_screenheight() - app.winfo_height()) / 2 - (30 * 1.5)
        app.geometry("+%d+%d" % (x, y))

# Ако имамо нових фактура за приказ, позивамо deiconify() након задавања коначне позиције прозора
if have_processed_invoices == True:
    app.deiconify()
else:
    # Затварамо апликацију
    app.destroy()

# Покрећемо главну петљу
app.mainloop()
