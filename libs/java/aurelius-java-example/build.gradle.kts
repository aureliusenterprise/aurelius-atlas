import com.github.davidmc24.gradle.plugin.avro.GenerateAvroJavaTask
import dev.nx.gradle.nx

nx {
    set("name", "aurelius-java-example")
    // @nx/gradle has no release support yet, so version this module from its
    // build script with our custom version actions (see tools/plugins).
    set("release") {
        set("version") {
            set("versionActions", "tools/plugins/gradle-version-actions.ts")
        }
    }
}

version = "0.6.1"

plugins {
    id("com.github.davidmc24.gradle.plugin.avro").version("1.9.1")
}

repositories {
    gradlePluginPortal()
}

dependencies {
    implementation(libs.avro)
}

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

tasks.named<Test>("test") {
    useJUnitPlatform()
}

allprojects {
    apply {
        plugin("project-report")
    }
}

tasks.register<GenerateAvroJavaTask>("generateAvro") {
    source("../../../schemas/avro")
    setOutputDir(file("src/main/java"))
}

tasks.register("projectReportAll") {
    allprojects.forEach {
        dependsOn(it.tasks.getAt("projectReport"))
    }

    gradle.includedBuilds.forEach {
        dependsOn(it.task(":projectReportAll"))
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
