import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.nio.charset.StandardCharsets;
import java.security.ProtectionDomain;
import java.util.Arrays;

/**
 * Neutralises Elasticsearch's bootstrap write to /proc/self/coredump_filter.
 *
 * <p>Elasticsearch 9.x writes "0x23" to /proc/self/coredump_filter at bootstrap
 * (to keep file-backed pages out of core dumps) and treats any failure as fatal
 * ("Could not set coredump filter", elastic/elasticsearch#139589 - closed
 * not-planned: "the environment must allow the write"). GKE's container
 * lockdown denies that procfs write to every docker container on the node
 * (Aurelius Atlas CI runs 40237701606..40273498229: every uid, --privileged,
 * --cgroup-parent kubepods.slice), while the setting is cosmetic in CI - no
 * core dumps are ever collected there.
 *
 * <p>This agent rewrites the path constant in the class bytes before
 * org.elasticsearch.bootstrap.Elasticsearch is defined, redirecting the write
 * to a writable file. The replacement is the SAME BYTE LENGTH so the class
 * file's constant-pool offsets stay valid (no ASM needed):
 * "/proc/self/coredump_filter" (26 bytes) -> "/tmp/coredump_filter.jvm12"
 * (26 bytes), a plain file on the container's tmpfs.
 */
public final class CoredumpNoopAgent {

    private static final byte[] OLD = "/proc/self/coredump_filter".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] NEW = "/tmp/coredump_filter.jvm12".getBytes(StandardCharsets.US_ASCII);

    private CoredumpNoopAgent() {}

    public static void premain(String args, Instrumentation inst) {
        inst.addTransformer(new Transformer(), false);
    }

    static final class Transformer implements ClassFileTransformer {
        @Override
        public byte[] transform(
                ClassLoader loader,
                String name,
                Class<?> clazz,
                ProtectionDomain pd,
                byte[] bytes) {
            if (bytes == null || !"org/elasticsearch/bootstrap/Elasticsearch".equals(name)) {
                return null;
            }
            int at = indexOf(bytes);
            if (at < 0) {
                return null; // upstream changed: do nothing, let ES fail loudly
            }
            byte[] patched = Arrays.copyOf(bytes, bytes.length);
            System.arraycopy(NEW, 0, patched, at, NEW.length);
            return patched;
        }

        private static int indexOf(byte[] haystack) {
            outer:
            for (int i = 0; i + OLD.length <= haystack.length; i++) {
                for (int j = 0; j < OLD.length; j++) {
                    if (haystack[i + j] != OLD[j]) {
                        continue outer;
                    }
                }
                return i;
            }
            return -1;
        }
    }
}
