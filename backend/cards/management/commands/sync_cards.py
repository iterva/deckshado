import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from cards.models import Edition, Format, Race, CardType, Rarity, Keyword, Card

# Todas las ediciones organizadas por formato
EDITIONS_BY_FORMAT = {
    "imp": [
        "kvsm_titanes",
        "libertadores",
        "onyria",
        "toolkit_cenizas_de_fuego",
        "toolkit_hielo_inmortal",
        "lootbox_2024",
        "secretos_arcanos",
        "bestiarium",
        "escuadronmecha",
        "amenazakaiju",
        "zodiaco",
        "espiritu_samurai",
    ],
    "imp_r": [
        "giger",
        "raciales_imp_2024",
        "napoleon",
        "chile_oscuro",
        "visiones_de_kemet",
        "la_venganza_de_horus",
        "extension_valhalla",
        "relatos_del_despertar_gotico",
        "neo_midgard",
        "valhalla",
        "guardianes_reino_dos",
        "guardianes_reino_uno",
        "mastertoolkit_2023",
        "explorandum",
        "despertar_gotico",
        "master_toolkit_2022",
        "coleccion_racial_2022",
        "cid",
        "cuentos_de_terror_lovecraft",
        "cuentos_de_terror_poe",
        "hermanos_grimm_elaguadelavida_y_johndeacero",
        "hermanos_grimm_elsastrecillovaliente_y_musicosdebremen",
        "tinta_inmortal_romeo_y_julieta",
        "tinta_inmortal_robin_hood",
        "acero",
        "escuelas_elementales",
        "ajedrez",
        "angeles-demonios",
        "conjuros",
        "tierra-austral",
        "cuentos-de-ultratumba",
        "keltoi",
        "hermanos-grimm",
        "dinastia-del-dragon",
        "invasion-oscura",
        "terrores-nocturnos",
        "tinta-inmortal",
        "arsenal",
        "kilimanjaro",
        "calavera",
        "olimpia",
        "dharma",
        "kemet",
        "legado-gotico",
        "hijos-del-sol",
        "axis-mundi",
        "steampunk",
        "aguila-imperial",
        "contraataque",
        "dominio",
        "sol-naciente",
        "bushido",
        "templarios",
        "camelot",
        "midgard",
        "asgard",
        "rebelion",
        "sumeria",
        "furiaext",
        "furia",
    ],
    "lbf": [
        "leyendas_bloque_furia",
    ],
    "fx": [
        "producto_especial_furia_aniversario",
        "guardianes_de_daana",
        "vigilantes",
        "guerreros_del_sol",
        "kingdom_quest",
        "extension_troya",
        "la_cofradia",
        "troya",
        "extension_excalibur",
        "excalibur",
        "mazos_fx",
        "leyendas_de_metal",
        "roma",
    ],
    "2b": [
        "promocionales_segundo_bloque",
        "leyendas_segundo_bloque",
        "heroes",
        "bestiario",
        "hordas",
        "reino_de_acero",
        "barbarie",
        "vendaval",
        "guerrero_jaguar",
    ],
    "pb": [
        "dante_pb",
        "shogun_iii",
        "daana_aniversario",
        "relatos_hel_laberinto_del_minotauro",
        "relatos_hel_camino_de_teseo",
        "relatos_hel_mar_de_poseidon",
        "toolkit_pb_magia_y_divinidad",
        "toolkit_pb_fuerza_y_destino",
        "leyendas_pb_3.0",
        "pb_lootbox_2023",
        "dracula_pb",
        "shogun_ii",
        "helenica_aniversario",
        "colecciones_raciales_pb_2023",
        "relatos_espada_sagrada_aniversario",
        "espada_sagrada_aniversario",
        "extensiones_pb_2023",
        "toolkit_fe_sin_limite",
        "toolkit_dragon_dorado",
        "primer_bloque_2",
        "shogun_1",
        "raciales_pb",
        "promocionales_primer_bloque",
        "leyendas_primer_bloque",
        "encrucijada",
        "dominios-de-ra",
        "tierras_altas",
        "hijos_de_daana",
        "imperio",
        "helenica",
        "cruzadas",
        "espada-sagrada",
    ],
    "pe": [
        "xinnian_año_serpiente_2025",
        "toolkit_valentia_y_desolacion",
        "toolkit_honor_y_ferocidad",
        "lootbox_pe_2024",
        "vigilantes_de_la_noche",
        "mundos_perdidos_senores_del_trueno",
        "mundos_perdidos_viaje_al_oeste",
        "mundos_perdidos_leyendas_de_avalon",
        "mundos_perdidos_la_saga_de_volsung",
        "mundos_perdidos_ciudad_de_los_cesares",
        "mundos_perdidos_horrores_de_salem",
        "toolkit_justa",
        "toolkit_puertas_del_valhalla",
        "xinnian",
        "mundo_medieval_el_reto",
        "leyendas_primera_era_2023",
        "toolkit_odin",
        "toolkit_walkirias",
        "leyendas_primera_era_2022",
        "eXtension_pe",
        "raciales_pe",
        "promocionales_primera_era",
        "leyendas_primera_era",
        "espiritu_del_dragon",
        "cofradia",
        "ragnarok",
        "ira_del_nahual",
        "mundo_gotico",
        "el_reto",
    ],
}

ALL_FORMATS = list(EDITIONS_BY_FORMAT.keys())

FORMAT_NAMES = {
    "imp": "Imperio",
    "imp_r": "Imperio (Rotado)",
    "lbf": "Leyendas Bloque Furia",
    "fx": "FX",
    "2b": "Segundo Bloque",
    "pb": "Primer Bloque",
    "pe": "Primera Era",
}

# Reverse mapping: slug -> format code
SLUG_TO_FORMAT = {}
for _fmt, _slugs in EDITIONS_BY_FORMAT.items():
    for _slug in _slugs:
        SLUG_TO_FORMAT[_slug] = _fmt


class Command(BaseCommand):
    help = "Sincroniza cartas desde la API oficial de Mitos y Leyendas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--edition",
            type=str,
            help="Slug de una edición específica a sincronizar",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=ALL_FORMATS + ["all"],
            help="Formato a sincronizar: imp, pb, fx, 2b, pe, lbf, o 'all' para todo",
        )

    def handle(self, *args, **options):
        base_url = settings.MYL_API_BASE_URL
        edition_slug = options.get("edition")
        fmt = options.get("format")

        # Ensure all Format objects exist in the DB
        for code, name in FORMAT_NAMES.items():
            Format.objects.get_or_create(code=code, defaults={"name": name})

        if edition_slug:
            slugs = [edition_slug]
        elif fmt == "all":
            slugs = []
            for f in ALL_FORMATS:
                slugs.extend(EDITIONS_BY_FORMAT[f])
        elif fmt:
            slugs = EDITIONS_BY_FORMAT[fmt]
        else:
            # Por defecto: solo IMP
            slugs = EDITIONS_BY_FORMAT["imp"]
            self.stdout.write("Sincronizando formato Imperio (IMP). Usa --format all para todo.\n")

        total_cards = 0
        for slug in slugs:
            url = f"{base_url}/cards/edition/{slug}"
            self.stdout.write(f"Consultando {url} ...")

            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
            except requests.RequestException as e:
                self.stderr.write(self.style.WARNING(f"  Error al consultar {slug}: {e}"))
                continue

            data = resp.json()
            if data.get("status") != "OK":
                self.stderr.write(self.style.WARNING(f"  Respuesta no OK para {slug}"))
                continue

            # Sync lookup tables
            self._sync_races(data.get("races", []))
            self._sync_types(data.get("types", []))
            self._sync_rarities(data.get("rarities", []))
            self._sync_keywords(data.get("keywords", []))

            # Sync edition
            ed_data = data.get("edition", {})
            ed_slug = ed_data["slug"]
            fmt_code = SLUG_TO_FORMAT.get(slug) or SLUG_TO_FORMAT.get(ed_slug)
            fmt_obj = Format.objects.filter(code=fmt_code).first() if fmt_code else None

            # imp_r (rotado) no está activo, el resto sí
            is_active = fmt_code != "imp_r"

            edition, _ = Edition.objects.update_or_create(
                myl_id=str(ed_data["id"]),
                defaults={
                    "slug": ed_slug,
                    "title": ed_data["title"],
                    "image": ed_data.get("image") or "",
                    "date_release": ed_data.get("date_release"),
                    "date_empire_valid": ed_data.get("date_empire_valid"),
                    "format": fmt_obj,
                    "active": is_active,
                },
            )

            # Sync cards
            cards_data = data.get("cards", [])
            for c in cards_data:
                rarity = None
                if c.get("rarity") is not None:
                    rarity = Rarity.objects.filter(myl_id=str(c["rarity"])).first()

                race = None
                if c.get("race") is not None:
                    race = Race.objects.filter(myl_id=str(c["race"])).first()

                card_type = None
                if c.get("type") is not None:
                    card_type = CardType.objects.filter(myl_id=str(c["type"])).first()

                Card.objects.update_or_create(
                    myl_id=str(c["id"]),
                    defaults={
                        "edid": c["edid"],
                        "slug": c["slug"],
                        "name": c["name"],
                        "edition": edition,
                        "rarity": rarity,
                        "race": race,
                        "card_type": card_type,
                        "cost": c.get("cost"),
                        "damage": c.get("damage"),
                        "ability": c.get("ability") or "",
                        "flavour": c.get("flavour") or "",
                    },
                )

            count = len(cards_data)
            total_cards += count
            self.stdout.write(self.style.SUCCESS(f"  {edition.title}: {count} cartas sincronizadas"))

        self.stdout.write(self.style.SUCCESS(f"\nTotal: {total_cards} cartas sincronizadas"))

    def _sync_races(self, races):
        for r in races:
            Race.objects.update_or_create(
                myl_id=str(r["id"]),
                defaults={"slug": r["slug"], "name": r["name"]},
            )

    def _sync_types(self, types):
        for t in types:
            CardType.objects.update_or_create(
                myl_id=str(t["id"]),
                defaults={"slug": t["slug"], "name": t["name"]},
            )

    def _sync_rarities(self, rarities):
        for r in rarities:
            Rarity.objects.update_or_create(
                myl_id=str(r["id"]),
                defaults={"slug": r["slug"], "name": r["name"]},
            )

    def _sync_keywords(self, keywords):
        for k in keywords:
            Keyword.objects.update_or_create(
                myl_id=str(k["id"]),
                defaults={
                    "flag": int(k["flag"]),
                    "slug": k["slug"],
                    "title": k["title"],
                    "alt_title": k.get("alt_title", ""),
                    "definition": k.get("definition", ""),
                },
            )
