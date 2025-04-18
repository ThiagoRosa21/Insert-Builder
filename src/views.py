from main import app
from flask import render_template, request, send_file
import pandas as pd
import os
import sqlite3

@app.route("/")
def homepage_view():
    return render_template("homepage.html")

@app.route("/process", methods=["POST"])
def invite_archive():
    file = request.files.get('file-upload')
    table = request.form.get('table-name')
    limit = request.form.get('limit')
    archive_type = request.form.get('archive_type')

    if not file:
        return "No file was uploaded."
    
    if not table:
        return "Table name is required."
    
    if not archive_type:
        return "File type is required."
    
    try:
        limit = int(limit) if limit else None
    except ValueError:
        return "Invalid limit value. Please provide a numeric value."

    try:
        if archive_type == "excel":
            df = pd.read_excel(file)
        elif archive_type == "csv":
            df = pd.read_csv(file)
        elif archive_type == "json":
            df = pd.read_json(file)
        else:
            return "Unsupported file type selected."
    except Exception as e:
        return f"Error processing the file: {str(e)}"

    if limit:
        df = df.head(limit)
    
    df.columns = [str(col).strip().replace(" ", "_") for col in df.columns]

    conn = sqlite3.connect("dados.db")
    cursor = conn.cursor()


    columns_def = []
    for col in df.columns:
        sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else ''
        if isinstance(sample_value, int):
            col_type = "INTEGER"
        elif isinstance(sample_value, float):
            col_type = "REAL"
        else:
            col_type = "TEXT"
        columns_def.append(f"{col} {col_type}")

   
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns_def)});")

  
    placeholders = ", ".join(["?"] * len(df.columns))
    insert_sql = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({placeholders})"

    for _, row in df.iterrows():
        cursor.execute(insert_sql, tuple(row.fillna(None)))

    conn.commit()

    inserts = []
    for _, row in df.iterrows():
        values = []
        for value in row:
            if pd.isnull(value):
                values.append("NULL")
            elif isinstance(value, str):
                escaped = value.replace("'", "''")
                values.append(f"'{escaped}'")
            else:
                values.append(str(value))
        insert_line = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(values)});"
        inserts.append(insert_line)

    output_file = os.path.join(os.path.dirname(__file__), 'inserts.sql')
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write("\n".join(inserts))

    conn.close()

    if not os.path.exists(output_file):
        return "Error: The output file was not generated."

    return send_file(
        output_file,
        as_attachment=True,
        download_name="inserts.sql",
        mimetype="text/plain"
    )
