package net.bullydiscs;

import net.fabricmc.api.ModInitializer;
import net.minecraft.item.Item;
import net.minecraft.item.MusicDiscItem;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.sound.SoundEvent;
import net.minecraft.util.Identifier;
import net.minecraft.util.Rarity;

public class BullyDiscs implements ModInitializer {

    public static final String MOD_ID = "bully_discs";

    // track ids in album order
    private static final String[] TRACKS = {
        "king", "this_a_must", "father", "all_the_love", "punch_drunk",
        "whatever_works", "mamas_favorite", "sisters_and_brothers", "bully",
        "highs_and_lows", "i_cant_wait", "white_lines", "circles",
        "preacher_man", "beauty_and_the_beast", "damn", "last_breath",
        "this_one_here", "losing_your_mind"
    };

    @Override
    public void onInitialize() {
        for (String track : TRACKS) {
            registerDisc(track);
        }
    }

    private void registerDisc(String track) {
        Identifier soundId = new Identifier(MOD_ID, track);
        SoundEvent registeredSound = Registry.register(Registries.SOUND_EVENT, soundId, SoundEvent.of(soundId));

        Identifier itemId = new Identifier(MOD_ID, "bully_disc_" + track);
        Rarity rarity = "this_one_here".equals(track) ? Rarity.EPIC : Rarity.RARE;
        Item disc = new MusicDiscItem(0, registeredSound, new Item.Settings()
                .maxCount(1)
                .rarity(rarity), 0);
        Registry.register(Registries.ITEM, itemId, disc);
    }
}
