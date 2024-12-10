from mcdreforged.api.all import *

psi = ServerInterface.psi()
plgSelf = psi.get_self_metadata()

def tr(tr_key: str):
    if tr_key.startswith(f"{plgSelf.id}"):
        translation = psi.rtr(f"{tr_key}")
    else:
        if tr_key.startswith("#"):
            translation = psi.rtr(tr_key.replace("#", ""))
        else:
            translation = psi.rtr(f"{plgSelf.id}.{tr_key}")
    translation: str = str(translation)
    return translation