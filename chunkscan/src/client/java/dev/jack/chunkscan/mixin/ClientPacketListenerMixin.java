package dev.jack.chunkscan.mixin;

import dev.jack.chunkscan.MenuObservations;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.network.protocol.game.ClientboundContainerSetContentPacket;
import net.minecraft.network.protocol.game.ClientboundOpenScreenPacket;
import net.minecraft.network.protocol.game.ClientboundContainerSetSlotPacket;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientPacketListener.class)
abstract class ClientPacketListenerMixin {
    @Inject(method = "handleOpenScreen", at = @At("RETURN"))
    private void chunkscan$opened(ClientboundOpenScreenPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.opened(this, packet.getContainerId());
    }

    @Inject(method = "handleContainerContent", at = @At("RETURN"))
    private void chunkscan$content(ClientboundContainerSetContentPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.content(this, packet.containerId(), packet.items());
    }

    @Inject(method = "handleContainerSetSlot", at = @At("RETURN"))
    private void chunkscan$slot(ClientboundContainerSetSlotPacket packet, CallbackInfo ci) {
        MenuObservations.LIVE.slot(this, packet.getContainerId(), packet.getSlot(), packet.getItem());
    }
}
