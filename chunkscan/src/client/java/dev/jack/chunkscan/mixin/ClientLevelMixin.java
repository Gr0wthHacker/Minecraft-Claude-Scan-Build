package dev.jack.chunkscan.mixin;

import dev.jack.chunkscan.PredictionAccess;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.multiplayer.prediction.BlockStatePredictionHandler;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(ClientLevel.class)
abstract class ClientLevelMixin implements PredictionAccess {
	@Shadow abstract BlockStatePredictionHandler getBlockStatePredictionHandler();
	@Unique private int chunkscan$ack = -1;
	public int chunkscan$sequence() { return getBlockStatePredictionHandler().currentSequence(); }
	public int chunkscan$acknowledged() { return chunkscan$ack; }
	@Inject(method = "handleBlockChangedAck", at = @At("RETURN"))
	private void chunkscan$afterAck(int sequence, CallbackInfo ci) {
		chunkscan$ack = Math.max(chunkscan$ack, sequence);
	}
}
