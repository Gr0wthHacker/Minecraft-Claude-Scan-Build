package dev.jack.chunkscan;

import com.google.gson.GsonBuilder;
import java.util.LinkedHashMap;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import java.nio.file.Files;
import java.nio.file.Path;

/** Read-only action-recipe coverage measurement for a frozen schematic. */
public final class ActionRecipeProbe {
    public static void main(String[] args) throws Exception {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        Path dir = Path.of(args[0]);
        var cells = Work.load(dir, args[1]);
        var report = ActionRecipe.missing(cells);
        Files.writeString(Path.of(args[2]), new GsonBuilder().setPrettyPrinting().create().toJson(report));
		if (args.length > 3) {
			var detail = new LinkedHashMap<String, Integer>();
			for (var cell : cells) {
				String family = ActionRecipe.missingFor(cell.block());
				if (family != null) detail.merge(family + " :: " + cell.block(), 1, Integer::sum);
			}
			Files.writeString(Path.of(args[3]), new GsonBuilder().setPrettyPrinting().create().toJson(detail));
		}
    }
}
