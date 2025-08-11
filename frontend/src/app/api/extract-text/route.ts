import { NextRequest, NextResponse } from "next/server";
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
// Import `auth` instead of `clerkClient`
import { auth } from "@clerk/nextjs/server";

export async function POST(request: NextRequest) {
  try {
    // Get auth from request using the auth() helper
    const { userId } = await auth();

    console.log("User ID:", userId);

    if (!userId) {
      return NextResponse.json(
        { error: "Authentication required" },
        { status: 401 }
      );
    }
    
    // The user object is now available directly from the request context
    // You no longer need to call clerkClient.users.getUser()
    // The user's ID is what you need for most operations.

    const formData = await request.formData();
    const file = formData.get("pdf") as File;
    const startPage = parseInt(formData.get("startPage") as string) || 1;
    const endPage = parseInt(formData.get("endPage") as string) || 1;

    // ... (rest of your code remains the same)
    if (!file) {
      return NextResponse.json(
        { error: "No PDF file provided" },
        { status: 400 }
      );
    }

    if (file.type !== "application/pdf") {
      return NextResponse.json(
        { error: "File must be a pdf" },
        { status: 400 }
      );
    }

    const bytes = await file.arrayBuffer();
    const blob = new Blob([bytes], { type: "application/pdf" });

    const loader = new PDFLoader(blob);
    const docs = await loader.load();

    if (
      startPage < 1 ||
      endPage < 1 ||
      startPage > docs.length ||
      endPage > docs.length
    ) {
      return NextResponse.json(
        { error: `Invalid page range. Document has ${docs.length} pages.` },
        { status: 400 }
      );
    }

    if (startPage > endPage) {
      return NextResponse.json(
        { error: "Start page cannot be greater than end page." },
        { status: 400 }
      );
    }

    const startIndex = startPage - 1;
    const endIndex = endPage - 1;
    const selectedPages = docs.slice(startIndex, endIndex + 1);

    const extractedText = selectedPages
      .map((doc) =>
        doc.pageContent.replace(/\s*\n\s*/g, " ").replace(/\s+/g, " ").trim()
      )
      .join("\n\n");

    return NextResponse.json({
      text: extractedText,
      pageCount: docs.length,
      extractedPages: `${startPage}-${endPage}`,
      totalExtractedPages: selectedPages.length,
      userId,
    });
  } catch (error) {
    console.error("Error extracting text from PDF:", error);
    return NextResponse.json(
      { error: "Failed to extract text from PDF" },
      { status: 500 }
    );
  }
}