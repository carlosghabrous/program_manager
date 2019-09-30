import pytest

from sqlalchemy                 import create_engine
from sqlalchemy                 import Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm             import sessionmaker
from sqlalchemy.sql             import text


def test_retrieve_data_from_pm_table_raw_statement():
    statement = text("""select HCR_CONTAINER from Alim.Program_Files_Parameters_View""")
    engine = create_engine(
        "oracle+cx_oracle://pocontrols_pm:P0cntrl2019!pm@(DESCRIPTION=(ADDRESS= (PROTOCOL=TCP) (HOST=pdb-s.cern.ch) (PORT=10121) )(ENABLE=BROKEN)(CONNECT_DATA=(SERVICE_NAME=pdb-s.cern.ch)))")

    with engine.connect() as conn:
        rs = conn.execute(statement)
        try:
            hcr_container = rs.fetchone()[0]

        except TypeError:
            hcr_container = ""

    print(hcr_container)

def test_retrieve_data_from_pm_table_with_class():
    conn_string = "oracle+cx_oracle://pocontrols:P0cntrl2019!@(DESCRIPTION=(ADDRESS= (PROTOCOL=TCP) (HOST=pdb-s.cern.ch) (PORT=10121) )(ENABLE=BROKEN)(CONNECT_DATA=(SERVICE_NAME=pdb-cerndb1.cern.ch)))"
    engine = create_engine(conn_string)
    Base = declarative_base()

    class FirmwareData(Base):
        __tablename__ = "Alim.Program_Files_Parameters_View"
        hcr_container    = Column(String, primary_key=True)
        device           = Column(String)
        board            = Column(String)
        component_type   = Column(String)
        variant          = Column(String)
        variant_revision = Column(String)
        api_revision     = Column(String)
        edms_location = Column(String)
        
    Session = sessionmaker(bind=engine)
    session = Session()
    for row in session.query(FirmwareData).all():
        print(row.hcr_container)
        
