package dev.jack.chunkscan;

import net.minecraft.client.Minecraft;
import net.minecraft.world.level.storage.LevelResource;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/** Evidence required before restoring unattended intent; not an action journal. */
record ResumeBinding(String world, String dimension, String inputs) {
    static ResumeBinding capture(Minecraft mc, Path dir, String design) throws IOException {
        if (mc.level == null) throw new IOException("world is unavailable");
        String world;
        if (mc.getSingleplayerServer() != null) {
            world = "local:" + mc.getSingleplayerServer().getWorldPath(LevelResource.ROOT).toRealPath();
        } else if (mc.getCurrentServer() != null && !mc.getCurrentServer().ip.isBlank()) {
            world = "server:" + mc.getCurrentServer().ip;
        } else throw new IOException("server identity is unavailable");
        return capture(dir, design, world, mc.level.dimension().identifier().toString());
    }

    static ResumeBinding capture(Path dir, String design, String world, String dimension) throws IOException {
        if (world == null || world.isBlank() || dimension == null || dimension.isBlank())
            throw new IOException("world identity is incomplete");
        Path work = Work.file(dir, design); // shared design-name validation
        Path schematic = dir.resolve(design + ".litematic");
        Path source = Files.exists(schematic) ? schematic : work;
        if (!Files.isRegularFile(source)) throw new IOException("build source is missing");
        Path side = dir.resolve(design + ".scan.json");
        if (source.equals(schematic) && !Files.isRegularFile(side))
            throw new IOException("schematic registration is missing");
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            // Include absence and names, not only concatenated bytes. Adding a registry or
            // switching from work JSON to a schematic changes the identity as well.
            for (Path path : new Path[]{source, side, dir.resolve("islands.json")}) {
                digest.update(path.getFileName().toString().getBytes(StandardCharsets.UTF_8));
                digest.update((byte) 0);
                if (!Files.exists(path)) { digest.update((byte) 0); continue; }
                digest.update((byte) 1);
                MessageDigest file = MessageDigest.getInstance("SHA-256");
                try (var in = Files.newInputStream(path)) {
                    byte[] buffer = new byte[65536];
                    int n;
                    while ((n = in.read(buffer)) != -1) file.update(buffer, 0, n);
                }
                digest.update(file.digest());
            }
            return new ResumeBinding(world, dimension, HexFormat.of().formatHex(digest.digest()));
        } catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }

    String mismatch(ResumeBinding current) {
        if (current == null) return "current world or input identity is unavailable";
        if (!java.util.Objects.equals(world, current.world)) return "server/world changed";
        if (!java.util.Objects.equals(dimension, current.dimension)) return "dimension changed";
        if (!java.util.Objects.equals(inputs, current.inputs)) return "schematic, registration or site registry changed";
        return null;
    }
}
