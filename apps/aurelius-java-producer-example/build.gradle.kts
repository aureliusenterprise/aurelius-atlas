import dev.nx.gradle.nx
import java.io.File

nx {
    set("name", "aurelius-java-producer-example")
    array("implicitDependencies", "aurelius-dev-kafka")
}

plugins {
    application
    id("jacoco")
}


repositories {
    mavenCentral()
    maven {
        url = uri("https://packages.confluent.io/maven/")
    }
}

dependencies {
    testImplementation(libs.junit.jupiter)
    testImplementation(libs.mockito.core)
    testImplementation(libs.mockito.junit.jupiter)

    testRuntimeOnly("org.junit.platform:junit-platform-launcher")

    // Local dependencies
    implementation(project(":aurelius-java-example"))

    // Kafka dependencies
    implementation(libs.kafka.avro.serializer)
    implementation(libs.kafka.clients)

    // Logging dependencies
    implementation(libs.slf4j.api)
    runtimeOnly(libs.slf4j.simple)

    // Other dependencies
    implementation(libs.jackson.core)
    // kafka-clients' OAUTHBEARER client-credentials JWT retriever needs
    // jackson-databind (declared optional upstream, so it is not transitively
    // brought in); without it token login fails at runtime with NoClassDefFoundError.
    implementation(libs.jackson.databind)
    // kafka-clients' OAUTHBEARER handler validates the fetched JWT with jose4j
    // (optional upstream dep, like jackson-databind): without it the login
    // callback handler fails with ClassNotFoundException at runtime.
    implementation(libs.jose4j)

    // OpenLineage dependencies
    // KafkaConfig and KafkaTransport are included in the main openlineage-java JAR
    implementation(libs.openlineage.java)

    constraints {
        // Kafka 8.3.2-ccs still bundles at.yawk.lz4:lz4-java 1.11.1, which Trivy
        // flags (CVE-2026-106449..106453); 1.12.0 is the patched release. The
        // at.yawk fork keeps the net.jpountz.* API kafka-clients calls, so the
        // upgrade is drop-in and the LZ4 record codec keeps working.
        implementation("at.yawk.lz4:lz4-java:1.12.0")
    }
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

application {
    mainClass = "com.aureliusenterprise.producer.App"
}

tasks.named<Test>("test") {
    useJUnitPlatform()
    finalizedBy(tasks.named("jacocoTestReport"))
}

/**
 * Loads a .env file and returns key-value pairs as a map.
 * Skips blank lines, comments, and handles surrounding quotes.
 */
fun loadEnv(file: File): Map<String, String> {
    val env = mutableMapOf<String, String>()
    if (!file.exists()) return env
    file.forEachLine { line ->
        val trimmed = line.trim()
        if (trimmed.isEmpty() || trimmed.startsWith("#")) return@forEachLine
        val parts = trimmed.split("=", limit = 2)
        if (parts.size < 2) return@forEachLine
        val key = parts[0].trim()
        var value = parts[1].trim()
        if (value.length >= 2) {
            if ((value.startsWith("\"") && value.endsWith("\"")) ||
                (value.startsWith("'") && value.endsWith("'"))) {
                value = value.substring(1, value.length - 1)
            }
        }
        env[key] = value
    }
    return env
}

// Inject .env values into the 'run' task's process environment
tasks.named("run", JavaExec::class).configure {
    val env = loadEnv(project.file("${projectDir}/.env"))
    environment(env)
    // The OAuth login (JWKS/token fetches from Keycloak) uses the JVM-wide
    // JSSE truststore, and Kafka 4.x requires the token URL in the OAuth URL
    // allowlist; both must be JVM system properties. Pass them here rather
    // than as JAVA_TOOL_OPTIONS in .env: Nx injects .env into EVERY task's
    // environment, so a JAVA_TOOL_OPTIONS there poisons unrelated JVMs
    // (sonar-scanner, the Gradle daemon's dependency downloads) with a
    // truststore path that only resolves from this project directory.
    // .env keys carry the AURELIUS_JAVA_PRODUCER_ prefix (AppConfig.ENV_PREFIX).
    env["AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_FILE"]?.takeIf { it.isNotBlank() }?.let { truststore ->
        systemProperty("javax.net.ssl.trustStore", project.file(truststore).absolutePath)
        // The password goes through the spawned JVM's environment, not a
        // command-line property: argv is world-readable (ps, /proc/<pid>/cmdline)
        // while a process's environment is owner-only on Linux. JAVA_TOOL_OPTIONS
        // here applies to THIS task's JVM only — unlike one in .env it cannot
        // poison other Nx tasks (see d80b06b3). The dev password is a single
        // token: JAVA_TOOL_OPTIONS is whitespace-split by the JVM launcher.
        environment(
            "JAVA_TOOL_OPTIONS",
            "-Djavax.net.ssl.trustStorePassword=${env["AURELIUS_JAVA_PRODUCER_KAFKA_TRUSTSTORE_PASSWORD"].orEmpty()}",
        )
    }
    env["AURELIUS_JAVA_PRODUCER_KAFKA_OAUTH_TOKEN_ENDPOINT_URL"]?.takeIf { it.isNotBlank() }?.let { tokenUrl ->
        systemProperty("org.apache.kafka.sasl.oauthbearer.allowed.urls", tokenUrl)
    }
    nx {
        // The producer verifies the broker against this project's truststore.
        array("dependsOn", "certgen")
    }
}

allprojects {
    apply {
        plugin("project-report")
    }
}

tasks.register("projectReportAll") {
    allprojects.forEach {
        dependsOn(it.tasks.getAt("projectReport"))
    }

    gradle.includedBuilds.forEach {
        dependsOn(it.task(":projectReportAll"))
    }
}

tasks.register("e2e") {
    group = "verification"
    nx {
        array("dependsOn") {
            add("decrypt")
            add("certgen")
            add("docker-build")
            obj {
                set("target", "up")
                set("dependencies", true)
            }
        }
        set("executor", "@nxlv/python:run-commands")
        set("metadata") {
            set("description", "Run the end-to-end tests for this application")
        }
        set("options") {
            set("command", "uv run pytest e2e")
            set("cwd", "{projectRoot}")
        }
    }
}

tasks.register("sonar") {
    nx {
        array("dependsOn", "decrypt", "build")
        set("command", "sonar-scanner -Dproject.settings={projectRoot}/sonar-project.properties -Dsonar.working.directory={projectRoot}/.scannerwork")
        set("metadata") {
            set("description", "Run SonarQube analysis on the project")
        }
    }
}

tasks.jacocoTestReport {
    group = "verification"
    description = "Run JaCoCo code coverage report for the test task"

    reports {
        xml.required.set(true)
        html.required.set(false)
        csv.required.set(false)
    }
}
