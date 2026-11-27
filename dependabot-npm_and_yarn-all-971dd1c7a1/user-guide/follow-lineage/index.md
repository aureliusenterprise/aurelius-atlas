# Follow lineage

Lineage shows where a dataset's data comes from and where it goes. The webapp draws it on the record page of a dataset or a process, so you read it beside the record rather than on a separate screen. The examples run on the imported sample catalogue, signed in as `demo_scientist`.

## Open the diagram

The diagram is a box on the page, not a link to somewhere else. On the dataset page it sits after **Child Datasets**, and on the process page after **Systems**. Two other things carry its name, and neither opens it: the stats-bar entry **Lineage Model** and the side navigation item scroll you to the box.

The box holds one of three states:

| What you see | What it means |
| --- | --- |
| Loading the lineage model... | The webapp is fetching the graph. |
| The diagram | The record has lineage, and this is it. |
| No lineage model available | The record has no lineage, or the lineage service failed. |

The empty message covers a failure on purpose. A record with no lineage and a broken service look the same here, so check the Alerts drawer to tell them apart: a failure files an error there, and a record with no lineage files nothing.

## Read the diagram

A model is a drawing of records and the flows between them, three steps wide in each direction from the record you opened. Two node kinds appear:

- A **dataset**, drawn as a light blue box with a database glyph.
- A **process**, drawn as a light teal box with a gear glyph.

A line runs from a dataset into a process, and out of a process into a dataset, and it carries an arrowhead. A relation with a name writes it along the line. The record you opened is drawn with a green outline, so you can find yourself on the page.

The webapp draws the first view of a model only. A model can hold more than one view, and you choose among them from the drawer described below.

The view below opens on the sample dataset `NL1-HR-001`, outlined in green, and runs right through the two processes it flows into.

![The lineage of NL1-HR-001.](<https://aureliusenterprise.github.io/dependabot-npm_and_yarn-all-971dd1c7a1/assets/user-guide/lineage-diagram.png>)

## Move around

Drag the drawing to pan it and scroll to zoom. The zoom stops at half size and at three times, and the diagram gives no warning when it hits either bound.

The toolbar icons on the box carry a tooltip and do one thing each:

| Icon | What it does |
| --- | --- |
| Browse the model | Opens the Details drawer on the Browse tab. |
| View info | Opens the Details drawer on the View tab. |
| Toggle fullscreen | Fills the screen with the drawing. |
| Reset zoom and pan | Returns the drawing to its start position and size. |
| Save view as image | Downloads the drawing as a PNG file. |

The keyboard works too. Tab to the drawing, then the arrow keys pan it and `+` and `-` zoom it. Tab on to a node and the arrows jump to the neighbour in that direction, and Enter selects it.

Saving downloads `<view name>.png`, usually `Lineage.png`, at the zoom you are looking at. The file carries the view name, the signed-in user's e-mail, and the version as metadata.

## Open one node

Click a node. The Details drawer slides in on the **Selection** tab, which names the node, its type, its description, its properties, and the concepts that reference it. The drawer's entity card links to that record's own page, and the URL of the drawer names the selected concept, so you can share it.

Clicking a connection selects the flow instead. Clicking the same node again clears the selection, and closing the drawer with the X, the scrim, Escape, or **Close** clears it too, so no node stays highlighted.

The drawer holds up to four tabs: **Browse** (pick a view from a dropdown, or walk the model tree), **Model** (search every element and relation in the model), **View** (the drawn view's own properties), and **Selection** (what you clicked). Choosing a view in **Browse** draws it and closes the drawer.

## Try it on the sample

1. Search for `NL1-HR-001` and open it. Scroll to the **Lineage Model** box. The stats bar reads **Available**, which means the diagram drew.
2. Read the drawing. The dataset sits against a process named **Analysed to**, which flows into the dataset **change-event**, which runs on into a process named **HR change connector**.
3. Click the **change-event** node. The drawer opens on its Selection tab. Open the entity card in the drawer to visit that dataset's own page.
4. Close the drawer, then click **Save view as image** to keep the picture.

If the box reads **No lineage model available** on a record you expected lineage on, open the Alerts drawer. An error there names the request that failed, which points at the lineage service.
