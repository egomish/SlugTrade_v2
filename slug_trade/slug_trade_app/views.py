from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.forms import formset_factory
import datetime
from .models import UserProfile
from slug_trade_app.forms import UserProfileForm, UserModelForm, ProfilePictureForm, ClosetItem, ClosetItemPhotos, \
    UserForm, SignupUserProfileForm, CashTransactionForm, OfferCommentForm

from . import models
from slug_trade_app.models import ItemImage, Item, Wishlist
from slug_trade_app.models import UserProfile
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

# Create your views here.
debug = False


def index(request):
    test = "This was passed from the backend!"
    if debug:
        print("in index view")
    return render(request, 'slug_trade_app/index.html', {'test': test})


def products(request):
    categories = [
        {'name': 'All', 'value': 'All'},
        {'name': 'Electronics', 'value': 'E'},
        {'name': 'Household goods', 'value': 'H'},
        {'name': 'Clothing', 'value': 'C'},
        {'name': 'Other', 'value': 'O'}
    ]
    if request.method == 'POST':
        if request.POST['category'] == 'All':
            items_list = ItemImage.objects.all()
        else:
            items_list = ItemImage.objects.all().filter(item__category=request.POST['category'])

        paginator = Paginator(items_list, 6)  # Show 6 items per page
        page = request.GET.get('page', 1)

        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            items = paginator.page(paginator.num_pages)

        return render(request, 'slug_trade_app/products.html',
                      {'items': items, 'categories': categories, 'last_category': request.POST['category']})

    else:
        if request.user.is_authenticated():
            items_list = ItemImage.objects.all()
            paginator = Paginator(items_list, 6)  # Show 6 items per page
            page = request.GET.get('page', 1)

            try:
                items = paginator.page(page)
            except PageNotAnInteger:
                items = paginator.page(1)
            except EmptyPage:
                items = paginator.page(paginator.num_pages)

            return render(request, 'slug_trade_app/products.html',
                          {'items': items, 'categories': categories, 'last_category': 'All'})

        else:
            return render(request, 'slug_trade_app/not_authenticated.html')


def show_users(request):
    users = User.objects.all()

    # for each user we want to get the
    if debug:
        for item in users:
            print(item.userprofile)
    return render(request, 'slug_trade_app/users.html', {'users': users})


def item_details(request, item_id=None):
    """
    primary purpose is to show user more about a specific item, and allow them to bid on it
    :param request: http request
    :param item_id: regexed number from url string that is item to inspect's item-id
    :return: a template with detailed information on the item with item_id, and the ability
    to continue further in the transaction process of trading
    """
    # Get the item with specified item id to load it's details

    # render the details into a useful dictionary object

    if not item_id:
        return render(request, 'slug_trade_app/not_authenticated.html')

    # load the item assosciated with item_id
    bid_item = models.Item.objects.get(id=item_id)
    # filter out all images that have a foreign key to the item we just found
    item_images = models.ItemImage.objects.get(item=item_id).get_image_list()
    # load the currently logged in users items

    print(item_images)
    # assembled the users items into a useful dictionary object

    # send that dictionary object to the template for rendering

    # remove spaces from trade type and makes lowercase for url. ex - Cash Only -> cash_only
    trade_type_name = bid_item.get_trade_options_display()
    trade_type_name = trade_type_name.replace(" ", "_").lower()

    return render(request, 'slug_trade_app/item_details.html', {'inspect_item': bid_item,
                                                                'item_photos': item_images,
                                                                'item_id': item_id,
                                                                'trade_type': trade_type_name,
                                                                })


def cash_transaction(request, item_id=None):

    if not request.user.is_authenticated():
        return redirect('/home')

    try:
        sale_item = Item.objects.get(id=item_id)
        if sale_item.trade_options is not '0':
            # redirect them to item details that is appropriate for this specific item
            return HttpResponse(f"This is not a trade item <a href='/item_details/{item_id}'>Go to this items details page</a>")
    except Exception as e:
        print(e)
        # send them a life preserver if they get lost
        return HttpResponse('This item does not exist <a href="/home">Go to home page<a>')

    if request.method == 'POST':
        # Process the form submission
        completed_cash_offer_form = CashTransactionForm(request.POST)
        completed_comment_offer_form = OfferCommentForm(request.POST)
        sale_item = Item.objects.get(id=item_id)
        if completed_cash_offer_form.is_valid() and completed_comment_offer_form.is_valid():

            item = models.Item.objects.get(id=item_id)
            print('type :', type(request.POST['comment']))
            cash_offer = models.CashOffer(
                item=item,
                offer_amount=request.POST['offer_amount'],
                original_bidder=request.user,
                current_bidder=request.user,
            )
            cash_offer.save()
            completed_comment_offer_form.item = sale_item
            completed_comment_offer_form.user = request.user
            completed_comment_offer_form.save()
            # if no comment is present do not save anything to the database

            if request.POST['comment']:
                print('>>>>>>Got a comment')
                offer_comment = models.OfferComment(
                    item=item,
                    # This is the user who made the comment
                    user=request.user,
                    comment=request.POST['comment']
                )
                offer_comment.save()
        return redirect('/home')

    else:
        # render the appropriate transaction form
        item = Item.objects.get(id=item_id)

        offer_comment_form = OfferCommentForm()
        # import cash offer form
        cash_transaction_form = CashTransactionForm()
        # TODO: Believe the below sale_item declaration is redundant (shadows clone in top scope)
        # too little time to test at the moment
        sale_item = Item.objects.get(id=item_id)
        print('>>>>>>>>>>> cash', sale_item.trade_options)
        sale_item_image = models.ItemImage.objects.get(item=item_id).get_image_list()[0]
        return render(request, 'slug_trade_app/transaction.html', {
            'transaction_type': 'cash',
            'sale_item': sale_item,
            'sale_item_image': sale_item_image,
            'cash_transaction_form': cash_transaction_form,
            'offer_comment_form': offer_comment_form
        })


def trade_transaction(request, item_id=None):
    # item_list = Item.objects.filter(user__id=request.user.id)
    """

    :param request: request from a user, maybe be a get or a post
    :param item_id: id for which the transaction is being placed on
    :return: redirect to home page, successfully save the transaction in the database with the models
    """

    # If user enters wrong id for some reason the item will not exist and redirect them to home
    # ensure that no incorrect querys ever end up in this view

    if not request.user.is_authenticated():
        return redirect('/home')

    try:
        sale_item = Item.objects.get(id=item_id)
        if sale_item.trade_options is not '2':
            # redirect them to item details that is appropriate for this specific item
            return HttpResponse(f"This is not a trade item <a href='/item_details/{item_id}'>Go to this items details page</a>")

    except Exception as e:
        print(e)
        # send them a life preserver if they get lost
        return HttpResponse('This item does not exist <a href="/home">Go to home page<a>')

    # preload the offer comment form with an offer comment object

    offer_comment_form = OfferCommentForm(request.POST)

    # get the currently logged in users items for sending to the template or the form
    logged_in_users_items = models.Item.objects.filter(user=request.user).values()

    for item_representation_dict in logged_in_users_items:
        # fore each get the image link for representation in the template
        item_representation_dict['image'] = models.ItemImage.objects.get(item=item_representation_dict['id']).get_image_list()[0]
    # process all of the strings in the form body into ints of item id's

    if request.method == 'POST':
        items_selected_for_trade = [int(item) for item in request.POST.getlist("selected-item")]
        for item in items_selected_for_trade:
            # print(item)
            # these are the items that were checked in the form, so for each we must add an item trade offer
            new_item_offer = models.ItemOffer(
                item_bid_on=sale_item,
                item_bid_with=models.Item.objects.get(id=item),
                item_owner=sale_item.user,
                original_bidder=request.user
            )
            new_item_offer.save()

        offer_comment_form.is_valid()
        # specify a default value for the comment as None, so that if there is a problem the code will terminate
        comment = offer_comment_form.cleaned_data.get('comment', None)

        if comment:
            # create an offer comment and save it to the database
            new_comment = models.OfferComment(
                item=sale_item,
                user=request.user,
                comment=comment,
            )
            new_comment.save()

        return redirect('/home')

        # # TODO:// offer comment is not currently working correctly


    else:
        # prepare the multi-field item form for rendering

        sale_item_image = models.ItemImage.objects.get(item=item_id).get_image_list()[0]

        offer_comment_form = OfferCommentForm()
        all_forms = []

        return render(request,
                      'slug_trade_app/transaction.html',
                      {'transaction_type': 'trade',
                       'sale_item': sale_item,
                       'offer_comment_form': offer_comment_form,
                       'logged_in_users_items': logged_in_users_items,
                       'sale_item_image': sale_item_image,
                       })


def free_transaction(request, item_id=None):

    if not request.user.is_authenticated():
        return redirect('/home')

    try:
        # check existence
        sale_item = Item.objects.get(id=item_id)
        # check free
        if sale_item.trade_options is not '3':
            # redirect them to item details that is appropriate for this specific item
            return HttpResponse(f"This is not a trade item <a href='/item_details/{item_id}'>Go to this items details page</a>")
    except Exception as e:
        print(e)
        # send them a life preserver if they get lost
        return HttpResponse('This item does not exist <a href="/home">Go to home page<a>')


    sale_item = Item.objects.get(id=item_id)
    print('>>>>>>>>>>> free', sale_item.trade_options)
    sale_item_image = models.ItemImage.objects.get(item=item_id).get_image_list()[0]

    return render(request, 'slug_trade_app/transaction.html', {'transaction_type': 'free',
                                                               'sale_item': sale_item,
                                                               'sale_item_image': sale_item_image,
                                                               })


def transaction(request, item_id=None):  # set default value for item id so it doesn't crash
    """
    Primary purpose is to place an offer from the current user
    consisting of one or more items from their inventory ONTO
    another item (described by item_id) that is owned by a different user
    :param request: req. obj
    :param item_id: describes the item that is currently being offered/bid on
    :return: redirects user to an arbitrary page after they complete the offer, sends
    the completed offer to an as-of-yet undetermined endpoint to process the offer.
    """

    if not item_id:
        return render(request, 'slug_trade_app/not_authenticated.html')

    # handle a form submission:
    if request.method == 'POST' and request.user.is_authenticated():
        print("it's a post!")
        # handle post
        form = TransactionForm(request.POST)
        return HttpResponse('test')

    else:
        # TODO: Uncomment below for final version, commented because logging in is repetitive
        # if  request.user.is_authenticated() and request.method == 'GET':
        if request.method == 'GET':
            item_list = Item.objects.filter(user__id=request.user.id)
            sale_item = Item.objects.get(id=item_id)
            return render(request, 'slug_trade_app/transaction.html',
                          {
                              'user_item_list': item_list,
                              'sale_item': sale_item
                          })


def public_profile_inspect(request, user_id):
    """
        :param request: http request obj
        :param user_id: database key for specific user to load details about
        REQUIREMENTS: user_id exists in the database and it corresponds correctly
        to a specific user (numbers outside
        :return: render template
    """

    # verify that the given user_id is in the database, and if no prompt a redirect
    if not User.objects.filter(id=user_id).exists():
        return HttpResponse('<h1>No user exists for your query <a href="/">Go home</a></h1>')

    if request.user.is_authenticated() and int(user_id) == int(request.user.id):
        return redirect('/profile')

    # get the user model object
    user_to_view = User.objects.get(id=user_id)

    # get all of the items for the given user
    items = Item.objects.filter(user__id=user_id)

    # get the list of each item's images from the models method get_image_list()
    images = [ItemImage.objects.get(item=item).get_image_list() for item in items]
    # print(images)

    # zip the two lists into one iterable together
    items_and_images = zip(items, images)
    print("Items and images: ", items_and_images)

    wishlist = Wishlist.objects.filter(user=User.objects.get(id=user_id))

    return render(request, 'slug_trade_app/profile.html', {
        'user': user_to_view,
        'public': True,
        'item_data': items_and_images,
        'wishlist': wishlist,
        'show_add_button': False
    })


def profile(request):
    """
        profile is the view that handles authenticated users who have logged in
        by default it displays relevant information about the user, if no user
        is logged in, it will redirect to a sign-up/broken page
    """
    if request.user.is_authenticated():
        if request.method == 'POST':
            # if the wishlist item already exists in the wishlist, do not add it again
            try:
                existing_item = Wishlist.objects.get(user=request.user,
                                                     wishlist_item_description=request.POST['description'])
            except Wishlist.DoesNotExist:
                item = Wishlist(
                    user=request.user,
                    wishlist_item_description=request.POST['description']
                )
                item.save()
                return redirect('/profile?item_added=True')

        wishlist = Wishlist.objects.filter(user=request.user)
        items = Item.objects.filter(user__id=request.user.id)
        images = [ItemImage.objects.get(item=item).get_image_list() for item in items]
        items_and_images = zip(items, images)
        return render(request, 'slug_trade_app/profile.html', {
            'user': request.user,
            'public': False,
            'item_data': items_and_images,
            'wishlist': wishlist,
            'show_add_button': True,
            'item_added': request.GET.get('item_added', False)
        })
    else:
        return render(request, 'slug_trade_app/not_authenticated.html')


@csrf_exempt
def delete_from_wishlist(request):
    Wishlist.objects.get(id=request.POST['id']).delete()
    return HttpResponse('Deleted!')


def edit_profile(request):
    if request.method == 'POST':
        user_instance = User.objects.get(id=request.user.id)
        user_profile_instance = user_instance.userprofile
        user_form = UserModelForm(request.POST, instance=user_instance)
        user_profile_form = UserProfileForm(request.POST, instance=user_profile_instance)
        profile_picture_form = ProfilePictureForm(request.POST, request.FILES)
        if user_form.is_valid():
            user_form.save()
        if user_profile_form.is_valid():
            user_profile_form.save()
        if profile_picture_form.is_valid() and request.FILES['file']:
            user_profile_instance.profile_picture = request.FILES['file']
            user_profile_instance.save()
        return redirect('/profile')
    else:
        if request.user.is_authenticated():
            user = User.objects.get(id=request.user.id)
            user_form = UserModelForm(instance=user)
            user_profile = user.userprofile
            user_profile_form = UserProfileForm(instance=user_profile)
            profile_picture_form = ProfilePictureForm()
            return render(request, 'slug_trade_app/edit_profile.html', {
                'user_form': user_form,
                'user_profile_form': user_profile_form,
                'profile_picture_form': profile_picture_form,
                'user': request.user
            })
        else:
            return render(request, 'slug_trade_app/not_authenticated.html')


def add_closet_item(request):
    if request.method == 'POST':
        form = ClosetItem(request.POST)
        photos = ClosetItemPhotos(request.POST, request.FILES)

        if form.is_valid():
            print('form is valid')
            item = form.save(commit=False)
            item.user = request.user
            if item.price < 0:
                item.price = 0
            form.save()

            if photos.is_valid():
                print('photos. is valid!')

                pics = []
                files = request.FILES

                if files.get('image1', False): pics.append(files['image1'])
                if files.get('image2', False): pics.append(files['image2'])
                if files.get('image3', False): pics.append(files['image3'])
                if files.get('image4', False): pics.append(files['image4'])
                if files.get('image5', False): pics.append(files['image5'])

                if len(pics) == 1:
                    insert = ItemImage(
                        item=item,
                        image1=pics[0]
                    )
                elif len(pics) == 2:
                    insert = ItemImage(
                        item=item,
                        image1=pics[0],
                        image2=pics[1]
                    )
                elif len(pics) == 3:
                    insert = ItemImage(
                        item=item,
                        image1=pics[0],
                        image2=pics[1],
                        image3=pics[2]
                    )
                elif len(pics) == 4:
                    insert = ItemImage(
                        item=item,
                        image1=pics[0],
                        image2=pics[1],
                        image3=pics[2],
                        image4=pics[3]
                    )
                elif len(pics) == 5:
                    insert = ItemImage(
                        item=item,
                        image1=pics[0],
                        image2=pics[1],
                        image3=pics[2],
                        image4=pics[3],
                        image5=pics[4]
                    )

                insert.save()

        return redirect('/profile')

    else:
        if request.user.is_authenticated():
            form = ClosetItem()
            photos = ClosetItemPhotos()
            return render(request, 'slug_trade_app/add_closet_item.html', {'form': form, 'photos': photos})
        else:
            return render(request, 'slug_trade_app/not_authenticated.html')


def signup(request):
    if request.user.is_authenticated():
        return redirect('/products')

    if request.method == 'POST':

        user_form = UserForm(request.POST)
        profile_form = SignupUserProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            # create user
            created_user = user_form.save()

            created_user.username = created_user.email
            created_user.set_password(user_form.cleaned_data.get('password1'))
            created_user.save()

            # create extended profile
            created_profile = profile_form.save(commit=False)

            profile = UserProfile(
                user=created_user,
                profile_picture=request.FILES['profile_picture'],
                bio=created_profile.bio,
                on_off_campus=created_profile.on_off_campus
            )
            profile.save()

            # authentication
            email = user_form.cleaned_data.get('email')
            password = user_form.cleaned_data.get('password1')

            authenticated = authenticate(
                username=email,
                password=password
            )
            # if user is authenticated log them in and redirect
            if authenticated:
                login(request, authenticated)
                return redirect('/products')
            else:
                print("not authenticated")
                return redirect('/home')
        else:
            print("NOT VALID")
            return render(request, 'slug_trade_app/signup.html', {'user_form': user_form,
                                                                  'profile_form': profile_form})

    else:
        user_form = UserForm()
        profile_form = SignupUserProfileForm()

        return render(request, 'slug_trade_app/signup.html', {'user_form': user_form,
                                                              'profile_form': profile_form,
                                                              })
