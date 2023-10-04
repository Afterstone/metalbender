import typing as t

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session as SessionType

from metalbender.config import (get_database_url, get_sql_client_cert_path,
                                get_sql_client_key_path,
                                get_sql_server_ca_path)
from metalbender.data_access import models  # noqa: F401
from metalbender.data_access._base import Base  # noqa: F401

ENGINE = create_engine(
    get_database_url(),
    connect_args={
        'sslmode': 'verify-ca',
        'sslrootcert': str(get_sql_server_ca_path().absolute()),
        'sslcert': str(get_sql_client_cert_path().absolute()),
        'sslkey': str(get_sql_client_key_path().absolute()),
    }
)

_SessionMaker = sessionmaker(bind=ENGINE)


def get_session() -> t.Generator[SessionType, None, None]:
    session = _SessionMaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
