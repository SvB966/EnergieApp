from typing import Dict, List, Optional
from collections import Counter

group_typeid_mapping: Dict[str, List[int]] = {
    # Elektriciteit
    "Hoofdmeting elektriciteit LDN": [1000, 1007, 1050, 1051, 1075, 1076, 1088, 1094],
    "Hoofdmeting elektriciteit ODN": [1001, 1005, 1077, 1078, 1089],
    "Controlemeting elektriciteit LDN": [1003, 1028],
    "Controlemeting elektriciteit ODN": [1004, 1020],
    "Bruto productie": [1006, 1008],
    "Controlemeting bruto productie": [1095],
    "Meting elektriciteit locale opwekking": [1009, 1024],
    # Blindvermogen
    "Hoofdmeting blindvermogen LDN": [1014, 1016],
    "Hoofdmeting blindvermogen ODN": [1017, 1022],
    "Controlemeting blindvermogen LDN": [1015, 1021],
    "Controlemeting blindvermogen ODN": [1018, 1023],
    "Tussenmeting blindvermogen ODN": [1116],
    # Tussenmetingen Elektriciteit
    "Tussenmeting elektriciteit LDN": [1042, 1059],
    "Tussenmeting elektriciteit ODN": [1074, 1079],
    # Overige (niet-elektriciteit)
    "Chloor": [1025],
    "Eigen verbruik van eigen energie": [1030],
    # Gasmetingen
    "Gas verbruik": [1032, 1049, 1061, 1069, 1091],
    "Gas verbruik herleid": [1033, 1052, 1066, 1082, 1083, 1084],
    "Flow": [1031, 1081],
    "Gas invoeding herleid": [1086],
    "Gas invoeding niet herleid": [1090],
    "Tussenmeting Gas": [1068, 1080],
    "Tussenmeting Gas verbruik herleid": [1092],
    "Tussenmeting Gas verbruik niet herleid": [1093],
    # Kilovoltampere
    "Hoofdmeting kilovoltampere LDN": [1072],
    "Controlemeting kilovoltampere LDN": [1070],
    "Hoofdmeting kilovoltampere ODN": [1073],
    "Controlemeting kilovoltampere ODN": [1071],
    # Virtuele en productie gerelateerde metingen
    "Sommatie Elektriciteit virtueel": [1038],
    "Verbruik productieeenheid": [1043, 1048],
    "Controlemeting verbruik productieeenheid": [1096],
    "Watermeting": [1044, 1053],
    "Kanaal voor E65": [1054],
    # Warmte/Koude
    "Warmtemeting": [1055, 1056],
    "Koudemeting": [1057, 1067],
    # Overige sensoren
    "Digitaal (aan/uit)": [1063],
    "Zuurstof": [1064],
    "Stroom": [1065],
    "Momenteel vermogen": [1035],
    "Momentele stroommeting": [1036],
    "Presentatie verbruik": [1037],
    "Spanning": [1039],
    "Stoomflow": [1040],
    "Temperatuur": [1041],
    "Zuurgraad": [1047],
    "Infocodes": [1102],
    # Rekenkanaal
    "Bruto Production Standen Rekenkanaal": [1103],
    "Verbruik Standen Rekenkanaal": [1104],
    "Virtueel Register Rekenkanaal": [1105],
    # Blindvermogen extra
    "Blindvermogen BP": [1106],
    "Blindvermogen Verbruik": [1107],
    # Laadpaal
    "Tussenmeting Laadpaal LDN": [1117, 1118],
    # Overige
    "Tijd": [1097],
    "Druk": [1098],
    "Calorische waarde": [1099],
    "Batterij capaciteit": [1100],
    "Luchtvochtigheid": [1101]
}

def get_typeids(group_name: str) -> List[int]:
    """Retrieve type IDs for a given measurement group."""
    if group_name not in group_typeid_mapping:
        raise KeyError(f"Unknown group '{group_name}'. Available groups: {list(group_typeid_mapping.keys())}")
    return group_typeid_mapping[group_name]


def list_groups() -> List[str]:
    """Return all available measurement groups."""
    return list(group_typeid_mapping.keys())


def validate_unique_ids() -> None:
    """Ensure no type ID appears in more than one group."""
    all_ids = [tid for ids in group_typeid_mapping.values() for tid in ids]
    dupes = [tid for tid, count in Counter(all_ids).items() if count > 1]
    if dupes:
        raise ValueError(f"Duplicate type IDs found across groups: {dupes}")


def add_group_mapping(group_name: str, typeids: List[int]) -> None:
    """Add a new measurement group mapping. Raises if group exists or IDs overlap."""
    if group_name in group_typeid_mapping:
        raise KeyError(f"Group '{group_name}' already exists.")
    overlap = set(typeids) & {tid for ids in group_typeid_mapping.values() for tid in ids}
    if overlap:
        raise ValueError(f"Cannot add mapping, these IDs already used: {sorted(overlap)}")
    group_typeid_mapping[group_name] = typeids
