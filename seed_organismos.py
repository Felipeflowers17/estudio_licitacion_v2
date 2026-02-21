import pandas as pd
from src.bd.database import SessionLocal, engine, Base
from src.bd.models import Organismo
from sqlalchemy import text

def cargar_organismos_desde_csv():
    print("="*60)
    print("🏗️ INICIANDO CARGA MASIVA DE ORGANISMOS")
    print("="*60)
    
    archivo_csv = "Listado organismos compradores.csv"
    
    try:
        # 1. Leer el CSV con Pandas
        # Usamos sep=';' porque tu archivo usa punto y coma
        # encoding='utf-8' o 'latin-1' según corresponda
        df = pd.read_csv(archivo_csv, sep=';', encoding='utf-8')
        
        print(f"✅ Archivo leído correctamente. Filas encontradas: {len(df)}")
        print("   Columnas detectadas:", df.columns.tolist())
        
        # 2. Conectar a la Base de Datos
        Base.metadata.create_all(bind=engine) # Asegura que la tabla exista
        session = SessionLocal()
        
        contador_nuevos = 0
        contador_existentes = 0
        
        print("\n⏳ Procesando registros...")
        
        # 3. Iterar y Guardar
        for index, row in df.iterrows():
            # Mapeo de columnas del CSV a tu Modelo
            # CSV: 'Código' -> BD: codigo (String)
            codigo_str = str(row['Código']).strip()
            
            # CSV: 'Nombre de la institución' -> BD: nombre
            nombre_org = str(row['Nombre de la institución']).strip()
            
            # (Opcional) Podríamos usar 'Sector' en el futuro
            # sector = row['Sector'] 
            
            # Verificamos si existe
            organismo_existente = session.query(Organismo).filter_by(codigo=codigo_str).first()
            
            if organismo_existente:
                # Si existe, actualizamos el nombre por si acaso (upsert)
                if organismo_existente.nombre != nombre_org:
                    organismo_existente.nombre = nombre_org
                contador_existentes += 1
            else:
                # Si no existe, lo creamos
                nuevo_org = Organismo(
                    codigo=codigo_str,
                    nombre=nombre_org,
                    puntaje=0 # Puntaje inicial neutro
                )
                session.add(nuevo_org)
                contador_nuevos += 1
            
            # Guardamos por lotes cada 100 registros para no saturar la RAM
            if index % 100 == 0:
                session.commit()
                print(f"   ... procesados {index} registros")
        
        # Commit final
        session.commit()
        
        print("\n" + "="*60)
        print("🎉 CARGA COMPLETADA EXITOSAMENTE")
        print(f"   • Organismos Nuevos agregados: {contador_nuevos}")
        print(f"   • Organismos Existentes actualizados: {contador_existentes}")
        print(f"   • Total en base de datos: {session.query(Organismo).count()}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"❌ Error: No se encuentra el archivo '{archivo_csv}' en la raíz.")
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    cargar_organismos_desde_csv()