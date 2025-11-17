# utils.py
def get_address_and_verb(hero):
    """
    Возвращает корректное обращение и глагол в прошедшем времени
    на основе поля 'gender' героя.
    """
    gender = getattr(hero, "gender", "мужской")  # по умолчанию — мужской
    name = hero.name

    if gender == "женский":
        address = f"дорогая {name}"
        verb = "обратилась"
    elif gender == "мужской":
        address = f"дорогой {name}"
        verb = "обратился"
    else:
        address = f"уважаемый герой {name}"
        verb = "обратился"

    return address, verb