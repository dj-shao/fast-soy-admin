from app.core.crud import CRUDBase
from app.system.models.dictionary import Dictionary
from app.system.schemas.dictionary import DictionaryCreate, DictionaryUpdate

dictionary_controller = CRUDBase[Dictionary, DictionaryCreate, DictionaryUpdate](model=Dictionary)
