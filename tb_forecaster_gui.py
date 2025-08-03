import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from PIL import Image

# ------------------- Конфігурація -------------------

# ------------------- Логотип і заголовок -------------------
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    
    st.markdown("<h2 style='text-align: center;'>TB-Forecaster — прогнозування туберкульозу</h2>", unsafe_allow_html=True)

st.markdown("""
<p style='text-align: center; font-size:16px'>Застосунок моделює кількість випадків туберкульозу у вибраній території на основі демографії, ризиків, даних минулих років та інтервенцій, використовуючи метод Пуассона.</p>
""", unsafe_allow_html=True)

# ------------------- Територія -------------------
districts = ["Бердянський", "Василівський", "Запорізький", "Мелітопольський", "Пологівський", "Запорізька область"]
territory = st.selectbox("Територія (район / область)", districts)

# ------------------- Період моделювання -------------------
model_period = st.radio("Який період прогнозується?", ["Воєнний", "Післявоєнний"])

# ------------------- Захворюваність -------------------
st.subheader("Показники захворюваності (можна додавати/видаляти рядки)")

if 'incidence_data' not in st.session_state:
    st.session_state.incidence_data = [{'year': '', 'value': '', 'period': 'Довоєнний'}]

def add_row():
    st.session_state.incidence_data.append({'year': '', 'value': '', 'period': 'Довоєнний'})

def remove_row(i):
    st.session_state.incidence_data.pop(i)

period_options = ["Довоєнний", "Воєнний", "Післявоєнний"]

for i, row in enumerate(st.session_state.incidence_data):
    cols = st.columns([2, 3, 3, 1])
    row['year'] = cols[0].text_input(f"Рік {i+1}", value=row['year'], key=f"year_{i}")
    row['value'] = cols[1].text_input(f"Захворюваність на 100 тис. {i+1}", value=row['value'], key=f"value_{i}", help="Використовуйте десяткові числа через крапку (наприклад, 56.4)")
    row['period'] = cols[2].selectbox(f"Період {i+1}", options=period_options, index=period_options.index(row['period']), key=f"period_{i}")
    if cols[3].button("🗑️", key=f"remove_{i}"):
        remove_row(i)
        st.rerun()

st.button("➕ Додати рядок", on_click=add_row)

# ------------------- Бактеріоскопічний статус та рецидиви -------------------
st.subheader("Бактеріоскопічний статус та рецидиви")
mbt_status = st.radio("Оберіть статус:", ["МБТ+", "МБТ−", "Не вказано"])
relapses_included = st.radio("Чи враховані випадки рецидивів?", ["Так", "Ні"])

# ------------------- Категорії населення -------------------
st.subheader("Оберіть переважаючу категорію населення")
age_group = st.selectbox("", [
    "Діти до 1 року", "Діти 1–4 роки", "Діти 5–9 років", "Діти 10–14 років", "Діти 15–17 років",
    "Дорослі: 18 років і старше"
])

# ------------------- Групи ризику -------------------
st.subheader("Переважаючі групи ризику")
risk_groups = st.multiselect("Оберіть групи:", [
    "Контактні особи", "Люди, що живуть з ВІЛ", "Особи з хронічними хворобами",
    "Шахтарі", "Медпрацівники", "Військові", "ВПО", "Ув'язнені та звільнені",
    "Курці", "Особи з алкогольною залежністю", "Літні люди (65+)",
    "Люди з інвалідністю", "Особи з низьким соціально-економічним статусом",
    "Люди, які не мають постійного місця проживання", "Мігранти",
    "Особи з резистентним ТБ в анамнезі", "Немовлята і діти до 5 років",
    "Вагітні жінки", "Підлітки", "Пацієнти з цукровим діабетом",
    "Особи після трансплантацій", "Пацієнти на імуносупресивній терапії", "Інші"
])

# ------------------- Тип ТБ -------------------
st.subheader("Категорія туберкульозу")
tb_type = st.radio("", ["Легеневий", "Позалегеневий"])

# ------------------- Демографія -------------------
st.subheader("Демографія")
population = st.number_input("Населення території (останній рік)", min_value=0, value=100000)
returnees = st.number_input("Очікуване повернення населення (осіб)", min_value=0, value=0)

# ------------------- Роки прогнозу -------------------
years_to_model = st.text_input("Кількість років для прогнозу (через кому)", "2025,2026,2027,2028,2029")

# ------------------- Інтервенції -------------------
st.subheader("Заплановані дії/втручання для впливу на ситуацію (необов'язково)")
intervention = st.radio("Чи проводяться або плануються інтервенції?", ["Так", "Ні"], index=1)
intervention_text = st.text_area(
    "Пояснення про заплановані дії/втручання",
    help="Уточніть заходи: активне виявлення, вакцинація, тощо.",
    placeholder="Наприклад: флюорографія серед ВПО..."
)

# ------------------- Розрахунок -------------------
if st.button("Змоделювати прогноз"):
    try:
        years = [int(row['year']) for row in st.session_state.incidence_data if row['year'] and row['value']]
        values = [float(row['value']) for row in st.session_state.incidence_data if row['year'] and row['value']]
        future_years = [int(y.strip()) for y in years_to_model.split(",")]

        X = np.log(np.array(years).reshape(-1, 1))
        y = np.log(np.array(values))
        a, b = np.polyfit(X.flatten(), y, deg=1)
        predictions = [np.exp(a * np.log(x) + b) for x in future_years]

        result_df = pd.DataFrame({
            "Рік": future_years,
            "Прогнозована захворюваність на 100 тис.": np.round(predictions, 2),
            "Прогнозована кількість випадків": np.round(np.array(predictions) * (population + returnees) / 100000).astype(int)
        })

        st.subheader("Результати прогнозу")
        st.dataframe(result_df)

        # --- Графік ---
        fig, ax = plt.subplots()
        ax.plot(years, values, label="Факт", marker="o")
        ax.plot(future_years, predictions, label="Прогноз", linestyle="--", marker="x")
        ax.set_xlabel("Рік")
        ax.set_ylabel("Захворюваність на 100 тис.")
        ax.set_title("Прогноз захворюваності на туберкульоз")
        ax.legend()
        st.pyplot(fig)

        # --- Збереження в PDF ---
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()
        elems = [Paragraph("Результати прогнозу TB-Forecaster", styles["Title"]), Spacer(1, 12)]

        data = [list(result_df.columns)] + result_df.values.tolist()
        table = Table(data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        elems.append(table)
        doc.build(elems)
        st.download_button("📄 Завантажити PDF", data=buffer.getvalue(), file_name="TB_forecast.pdf")

    except Exception as e:
        st.error(f"Помилка під час розрахунку: {e}")