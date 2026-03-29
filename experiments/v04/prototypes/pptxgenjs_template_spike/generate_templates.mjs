import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import pptxgen from "pptxgenjs";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const generatedDir = path.join(__dirname, "generated");
const specsPath = path.join(__dirname, "template_specs.json");
const imageLikePlaceholderTypes = new Set(["image", "pic", "picture"]);
const neutralTextStyle = {
  color: "333333",
  fontFace: "Arial",
  fontSize: 20,
  margin: 0.05,
  valign: "mid",
};

function placeholderObject(definition) {
  const options = {
    name: definition.name,
    type: definition.type,
    x: definition.x,
    y: definition.y,
    w: definition.w,
    h: definition.h,
    ...neutralTextStyle,
    ...(definition.options ?? {}),
  };

  const isImageLikePlaceholder =
    definition.placeholderKind === "image"
    || imageLikePlaceholderTypes.has(definition.type);

  if (isImageLikePlaceholder) {
    delete options.color;
    delete options.fontFace;
    delete options.fontSize;
    delete options.margin;
    delete options.valign;
    return { placeholder: { options } };
  }

  return {
    placeholder: {
      options,
      text: definition.text ?? "",
    },
  };
}

function resolveMasterObject(objectDefinition) {
  if (objectDefinition.image?.path) {
    return {
      image: {
        ...objectDefinition.image,
        path: path.join(__dirname, objectDefinition.image.path),
      },
    };
  }
  return objectDefinition;
}

function buildMasterObjects(specification, key) {
  const decorationKey = `${key}Decorations`;
  const placeholderKey = `${key}Placeholders`;
  return [
    ...(specification[decorationKey] ?? []).map(resolveMasterObject),
    ...(specification[placeholderKey] ?? []).map(placeholderObject),
  ];
}

function addPreviewSlide(presentation, masterName, previewDefinition) {
  const slide = presentation.addSlide({ masterName });
  for (const assignment of previewDefinition.textAssignments ?? []) {
    slide.addText(assignment.text, {
      placeholder: assignment.placeholder,
      ...neutralTextStyle,
    });
  }
  for (const assignment of previewDefinition.imageAssignments ?? []) {
    slide.addImage({
      placeholder: assignment.placeholder,
      path: path.join(__dirname, assignment.path),
    });
  }
  return slide;
}

async function generateTemplate(specification) {
  const presentation = new pptxgen();
  presentation.layout = "LAYOUT_WIDE";
  presentation.author = "autoreport contributors";
  presentation.company = "autoreport";
  presentation.subject = "v0.4 PptxGenJS template-authoring spike";
  presentation.title = specification.filename;
  presentation.lang = "en-US";

  presentation.defineSlideMaster({
    title: specification.titleLayoutName,
    background: { color: "FFFFFF" },
    objects: buildMasterObjects(specification, "title"),
  });
  presentation.defineSlideMaster({
    title: specification.bodyLayoutName,
    background: { color: "FFFFFF" },
    objects: buildMasterObjects(specification, "body"),
  });

  addPreviewSlide(
    presentation,
    specification.titleLayoutName,
    specification.previewSlides.title,
  );
  addPreviewSlide(
    presentation,
    specification.bodyLayoutName,
    specification.previewSlides.body,
  );

  const outputPath = path.join(generatedDir, specification.filename);
  await presentation.writeFile({ fileName: outputPath });
  return outputPath;
}

async function main() {
  await fs.mkdir(generatedDir, { recursive: true });
  const raw = await fs.readFile(specsPath, "utf8");
  const specifications = JSON.parse(raw);
  const outputs = [];
  for (const specification of specifications) {
    const outputPath = await generateTemplate(specification);
    outputs.push({
      id: specification.id,
      file: outputPath,
    });
  }
  console.log(JSON.stringify({ outputs }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
