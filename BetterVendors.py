import unrealsdk
from Mods.ModMenu import EnabledSaveType, Hook, ModTypes, RegisterMod, SDKMod, Options

class BetterVendors(SDKMod):
    Name: str = "Better Vendors"
    Author: str = "Orion"
    Description: str = "Better Vendors - IOTD 10% Legendary"
    Version: str = "1.1"
    Types: ModTypes = ModTypes.Gameplay
    SaveEnabledState: EnabledSaveType = EnabledSaveType.LoadWithSettings

    _weapons_patched: bool = False
    _health_patched: bool = False
    _iotd_patched: bool = False

    def __init__(self):
        self.Options = [
            Options.Slider(
                Caption="Level Threshold",
                Description="Vendors will sell Rare/VeryRare gear above this level.",
                StartingValue=15,
                MinValue=1,
                MaxValue=72,
                Increment=1,
            )
        ]

    def _get_threshold(self) -> int:
        return int(self.Options[0].CurrentValue)

    def _find(self, cls: str, path: str):
        obj = unrealsdk.FindObject(cls, path)
        if obj is None:
            unrealsdk.Log(f"[BetterVendors] WARNING: Could not find {cls} at '{path}'")
        return obj

    def _get_level(self, caller: unrealsdk.UObject) -> int:
        try:
            level = int(caller.GetGameStage())
            return level if level > 0 else 72  # Return 72 as fallback
        except Exception:
            return 72  # Return 72 as fallback

    def _patch_weapon_vendor(self) -> None:
        if self._weapons_patched:
            return

        pools = ["AssaultRifles", "Pistols", "Shotguns", "SMG", "SniperRifles", "Launchers"]
        any_patched = False

        for p in pools:
            target = self._find("ItemPoolDefinition", f"GD_ItemPools_Shop.WeaponPools.ShopPool_Weapons_{p}")
            rare   = self._find("ItemPoolDefinition", f"GD_Itempools.WeaponPools.Pool_Weapons_{p}_04_Rare")
            vrare  = self._find("ItemPoolDefinition", f"GD_Itempools.WeaponPools.Pool_Weapons_{p}_05_VeryRare")

            if target and rare and vrare:
                target.BalancedItems = [
                    (rare,  None, (1.0, None, None, 1.0), True),
                    (vrare, None, (1.0, None, None, 1.0), True),
                ]
                any_patched = True
                unrealsdk.Log(f"[BetterVendors] Patched weapon pool: {p}")
            else:
                unrealsdk.Log(f"[BetterVendors] Skipped weapon pool (missing object): {p}")

        if any_patched:
            self._weapons_patched = True

    def _patch_health_vendor(self) -> None:
        if self._health_patched:
            return

        objects = {
            "shields_rare":  ("ItemPoolDefinition", "GD_Itempools.ShieldPools.Pool_Shields_All_04_Rare"),
            "shields_vrare": ("ItemPoolDefinition", "GD_Itempools.ShieldPools.Pool_Shields_All_05_VeryRare"),
            "com_rare":      ("ItemPoolDefinition", "GD_Itempools.ClassModPools.Pool_ClassMod_04_Rare"),
            "com_vrare":     ("ItemPoolDefinition", "GD_Itempools.ClassModPools.Pool_ClassMod_05_VeryRare"),
            "relic_rare":    ("ItemPoolDefinition", "GD_Itempools.ArtifactPools.Pool_Artifacts_03_Rare"),
            "relic_vrare":   ("ItemPoolDefinition", "GD_Itempools.ArtifactPools.Pool_Artifacts_04_VeryRare"),
            "health_pool":   ("ItemPoolDefinition", "GD_ItemPools_Shop.HealthShop.HealthShop_Items"),
        }

        resolved = {}
        all_found = True

        for name, (cls, path) in objects.items():
            obj = unrealsdk.FindObject(cls, path)
            if obj is None:
                unrealsdk.Log(f"[BetterVendors] MISSING: {name} -> {path}")
                all_found = False
            else:
                unrealsdk.Log(f"[BetterVendors] Found: {name}")
                resolved[name] = obj

        if not all_found:
            unrealsdk.Log("[BetterVendors] Health vendor patch ABORTED: one or more objects not found (see above)")
            return

        # Weights: shields ~48%, COMs ~29%, relics ~17%
        resolved["health_pool"].BalancedItems = [
            (resolved["shields_rare"],  None, (1.0, None, None, 1.0), True),
            (resolved["shields_vrare"], None, (1.0, None, None, 1.0), True),
            (resolved["com_rare"],      None, (1.0, None, None, 0.5), True),
            (resolved["com_vrare"],     None, (1.0, None, None, 0.5), True),
            (resolved["relic_rare"],    None, (1.0, None, None, 0.3), True),
            (resolved["relic_vrare"],   None, (1.0, None, None, 0.3), True),
        ]

        unrealsdk.Log("[BetterVendors] Health vendor patched successfully (shields ~48%, COMs ~29%, relics ~17%)")
        self._health_patched = True

    def _patch_iotd(self) -> None:
        if self._iotd_patched:
            return

        uncommon = self._find(
            "ConstantAttributeValueResolver",
            "GD_ItemPools_Shop.Misc.Att_IOTD_Weighting_03_Uncommon:ConstantAttributeValueResolver_1"
        )
        rare_i = self._find(
            "ConstantAttributeValueResolver",
            "GD_ItemPools_Shop.Misc.Att_IOTD_Weighting_04_Rare:ConstantAttributeValueResolver_0"
        )
        vrare_i = self._find(
            "ConstantAttributeValueResolver",
            "GD_ItemPools_Shop.Misc.Att_IOTD_Weighting_05_VeryRare:ConstantAttributeValueResolver_0"
        )
        leg = self._find(
            "ConstantAttributeValueResolver",
            "GD_ItemPools_Shop.Misc.Att_IOTD_Weighting_06_Legendary:ConstantAttributeValueResolver_0"
        )

        if uncommon: uncommon.ConstantValue = 0.0
        if rare_i:   rare_i.ConstantValue   = 0.0
        if vrare_i:  vrare_i.ConstantValue  = 0.9
        if leg:      leg.ConstantValue      = 0.1

        if any([uncommon, rare_i, vrare_i, leg]):
            unrealsdk.Log("[BetterVendors] IOTD patched (90% VeryRare, 10% Legendary)")
            self._iotd_patched = True
        else:
            unrealsdk.Log("[BetterVendors] IOTD patch ABORTED: no objects found")

    def _apply_patches(self, caller: unrealsdk.UObject) -> None:
        level = self._get_level(caller)
        if level < self._get_threshold():
            unrealsdk.Log(f"[BetterVendors] Below threshold ({level} < {self._get_threshold()}), skipping")
            return

        if caller.ShopType == 0:
            unrealsdk.Log("[BetterVendors] Applying weapon vendor patches...")
            self._patch_weapon_vendor()
            self._patch_iotd()
        elif caller.ShopType == 1:
            unrealsdk.Log("[BetterVendors] Applying health vendor patches...")
            self._patch_health_vendor()
            self._patch_iotd()
        else:
            unrealsdk.Log(f"[BetterVendors] Unknown ShopType={caller.ShopType}, skipping")

    def ModOptionChanged(self, option, new_value) -> None:
        self._weapons_patched = False
        self._health_patched = False
        self._iotd_patched = False
        unrealsdk.Log("[BetterVendors] Options changed, patches reset")

    @Hook("WillowGame.WillowInteractiveObject.InitializeFromDefinition")
    def InitializeFromDefinition(
        self,
        caller: unrealsdk.UObject,
        function: unrealsdk.UFunction,
        params: unrealsdk.FStruct,
    ) -> bool:
        if caller.Class.Name != "WillowVendingMachine":
            return True

        # Reset so patches re-apply fresh each time a vendor initializes
        self._weapons_patched = False
        self._health_patched = False
        self._iotd_patched = False

        unrealsdk.Log(f"[BetterVendors] Vendor init - ShopType={caller.ShopType}, Level={self._get_level(caller)}, Threshold={self._get_threshold()}")
        self._apply_patches(caller)
        return True

    @Hook("WillowGame.WillowVendingMachine.SetItemOfTheDayTimer")
    def OnVendorRestock(
        self,
        caller: unrealsdk.UObject,
        function: unrealsdk.UFunction,
        params: unrealsdk.FStruct,
    ) -> bool:
        # Reset so patches re-apply right before the vendor reads the pools
        self._weapons_patched = False
        self._health_patched = False
        self._iotd_patched = False

        unrealsdk.Log(f"[BetterVendors] Vendor restock - ShopType={caller.ShopType}, Level={self._get_level(caller)}")
        self._apply_patches(caller)
        return True

    @Hook("WillowGame.WillowGameInfo.InitGame")
    def OnMapLoad(
        self,
        caller: unrealsdk.UObject,
        function: unrealsdk.UFunction,
        params: unrealsdk.FStruct,
    ) -> bool:
        self._weapons_patched = False
        self._health_patched = False
        self._iotd_patched = False
        unrealsdk.Log("[BetterVendors] Map loaded, patches reset")
        return True

RegisterMod(BetterVendors())
